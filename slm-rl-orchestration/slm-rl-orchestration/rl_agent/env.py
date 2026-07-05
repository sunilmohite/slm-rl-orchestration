"""
Custom Gymnasium environment for RL-based pod scaling.

State  (4 values, normalized-ish):
    [request_rate_rps, p95_latency_seconds, avg_cpu_cores, current_replicas]

Action (discrete, 3 values):
    0 = scale down by 1
    1 = no-op
    2 = scale up by 1

Reward:
    - large penalty if p95 latency exceeds SLO (violates user experience)
    - small penalty per replica (cost of running extra pods)
    - encourages: fewest replicas that keep latency under SLO

This directly implements the comparison your dissertation describes:
RL agent (multi-metric, proactive) vs HPA (single-metric CPU, reactive).
"""
import os
import time
import requests
from kubernetes import client, config
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NAMESPACE = "slm-rl-demo"
DEPLOYMENT = "slm-inference"
LATENCY_SLO_SECONDS = 1.5
MIN_REPLICAS = 1
MAX_REPLICAS = 5


class SLMScalingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, prometheus_url=None, prometheus_token=None, step_seconds=15):
        super().__init__()
        self.prom_url = prometheus_url or os.environ["PROMETHEUS_URL"]
        self.prom_token = prometheus_token or os.environ["PROMETHEUS_TOKEN"]
        self.step_seconds = step_seconds

        # observation: [request_rate, p95_latency, avg_cpu, replicas] all float32
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, MIN_REPLICAS], dtype=np.float32),
            high=np.array([100, 30, 10, MAX_REPLICAS], dtype=np.float32),
        )
        self.action_space = spaces.Discrete(3)  # down / no-op / up

        config.load_kube_config()

        configuration = client.Configuration.get_default_copy()
        configuration.verify_ssl = False
        client.Configuration.set_default(configuration)
        self.apps_api = client.AppsV1Api()
        self._last_obs = None

        

    # ---------------- Prometheus helpers ----------------
    def _query_prom(self, promql):
        r = requests.get(
            f"{self.prom_url}/api/v1/query",
            params={"query": promql},
            headers={"Authorization": f"Bearer {self.prom_token}"},
            verify=False,
            timeout=10,
        )
        r.raise_for_status()
        result = r.json()["data"]["result"]
        if not result:
            return 0.0
        return float(result[0]["value"][1])

    def _get_request_rate(self):
        q = f'sum(rate(slm_requests_total{{namespace="{NAMESPACE}"}}[1m]))'
        return self._query_prom(q)

    def _get_p95_latency(self):
        q = (
            f'histogram_quantile(0.95, sum(rate('
            f'slm_request_latency_seconds_bucket{{namespace="{NAMESPACE}"}}[1m])) by (le))'
        )
        return self._query_prom(q)

    def _get_avg_cpu(self):
        q = (
            f'sum(rate(container_cpu_usage_seconds_total{{'
            f'namespace="{NAMESPACE}", pod=~"{DEPLOYMENT}.*"}}[1m]))'
        )
        return self._query_prom(q)

    # ---------------- Kubernetes helpers ----------------
    def _get_replicas(self):
        dep = self.apps_api.read_namespaced_deployment(DEPLOYMENT, NAMESPACE)
        return dep.spec.replicas

    def _set_replicas(self, n):
        n = int(np.clip(n, MIN_REPLICAS, MAX_REPLICAS))
        body = {"spec": {"replicas": n}}
        self.apps_api.patch_namespaced_deployment_scale(DEPLOYMENT, NAMESPACE, body)
        return n

    # ---------------- Gym API ----------------
    def _observe(self):
        rps = self._get_request_rate()
        p95 = self._get_p95_latency()
        cpu = self._get_avg_cpu()
        replicas = self._get_replicas()
        obs = np.array([rps, p95, cpu, replicas], dtype=np.float32)
        self._last_obs = obs
        return obs

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._set_replicas(MIN_REPLICAS)
        time.sleep(self.step_seconds)  # let metrics settle
        obs = self._observe()
        return obs, {}

    def step(self, action):
        current = self._get_replicas()
        if action == 0:
            new_replicas = current - 1
        elif action == 2:
            new_replicas = current + 1
        else:
            new_replicas = current

        actual = self._set_replicas(new_replicas)

        # wait for the effect of this action to show up in metrics
        time.sleep(self.step_seconds)

        obs = self._observe()
        rps, p95, cpu, replicas = obs

        # ---- reward shaping ----
        reward = 0.0
        if p95 > LATENCY_SLO_SECONDS:
            reward -= 10.0 * (p95 - LATENCY_SLO_SECONDS)  # SLO violation penalty
        reward -= 0.5 * replicas  # cost penalty per running replica

        terminated = False
        truncated = False
        info = {"replicas": replicas, "p95_latency": p95, "request_rate": rps, "cpu": cpu}
        return obs, reward, terminated, truncated, info
