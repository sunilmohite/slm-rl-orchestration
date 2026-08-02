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

        self.prom_url = prometheus_url or os.getenv(
            "PROMETHEUS_URL",
            "https://localhost:9090"
        )

        self.prom_token = prometheus_token or os.getenv(
            "PROMETHEUS_TOKEN",
            "dummy_token_123"
        )

        self.step_seconds = step_seconds

        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, MIN_REPLICAS], dtype=np.float32),
            high=np.array([1000, 10, 10, MAX_REPLICAS], dtype=np.float32),
        )

        self.action_space = spaces.Discrete(3)

        config.load_kube_config()

        configuration = client.Configuration.get_default_copy()
        configuration.verify_ssl = False
        client.Configuration.set_default(configuration)

        self.apps_api = client.AppsV1Api()

    # -----------------------------------------------------
    # Generic Prometheus Query
    # -----------------------------------------------------

    def _query_prom(self, promql):

        try:

            r = requests.get(
                f"{self.prom_url}/api/v1/query",
                params={"query": promql},
                headers={"Authorization": f"Bearer {self.prom_token}"},
                verify=False,
                timeout=10,
            )

            if r.status_code != 200:
                print("\nPROMQL FAILED")
                print(promql)
                print(r.text)
                return 0.0

            result = r.json()["data"]["result"]

            if len(result) == 0:
                return 0.0

            return float(result[0]["value"][1])

        except Exception as e:
            print(e)
            return 0.0

    # -----------------------------------------------------
    # Metrics
    # -----------------------------------------------------

    def _get_request_rate(self):

        query = (
            f'sum(rate(slm_requests_total{{namespace="{NAMESPACE}"}}[1m]))'
        )

        return self._query_prom(query)

    def _get_p95_latency(self):

        query = (
            f'histogram_quantile('
            f'0.95,'
            f'sum(rate(slm_request_latency_seconds_bucket{{namespace="{NAMESPACE}"}}[1m])) by (le)'
            f')'
        )

        return self._query_prom(query)

    def _get_avg_cpu(self):

        query = (
            f'sum(rate(container_cpu_usage_seconds_total{{'
            f'namespace="{NAMESPACE}",'
            f'pod=~"{DEPLOYMENT}.*"'
            f'}}[1m]))'
        )

        return self._query_prom(query)

    # -----------------------------------------------------
    # Kubernetes
    # -----------------------------------------------------

    def _get_replicas(self):

        dep = self.apps_api.read_namespaced_deployment(
            DEPLOYMENT,
            NAMESPACE,
        )

        return dep.spec.replicas

    def _set_replicas(self, replicas):

        replicas = max(
            MIN_REPLICAS,
            min(MAX_REPLICAS, replicas)
        )

        body = {
            "spec": {
                "replicas": replicas
            }
        }

        self.apps_api.patch_namespaced_deployment_scale(
            DEPLOYMENT,
            NAMESPACE,
            body,
        )

        return replicas

    # -----------------------------------------------------
    # Observation
    # -----------------------------------------------------

    def _observe(self):

        rps = self._get_request_rate()
        latency = self._get_p95_latency()
        cpu = self._get_avg_cpu()
        replicas = self._get_replicas()

        return np.array(
            [
                rps,
                latency,
                cpu,
                replicas,
            ],
            dtype=np.float32,
        )

    # -----------------------------------------------------
    # Gym
    # -----------------------------------------------------

    def reset(self, seed=None, options=None):

        super().reset(seed=seed)

        self._set_replicas(MIN_REPLICAS)

        time.sleep(self.step_seconds)

        return self._observe(), {}

    def step(self, action):

        replicas = self._get_replicas()

        if action == 0:
            replicas -= 1

        elif action == 2:
            replicas += 1

        self._set_replicas(replicas)

        time.sleep(self.step_seconds)

        obs = self._observe()

        rps = obs[0]
        latency = obs[1]
        cpu = obs[2]
        replicas = obs[3]

        reward = 0

        if latency > LATENCY_SLO_SECONDS:
            reward -= 10 * (latency - LATENCY_SLO_SECONDS)

        reward -= 0.5 * replicas

        info = {
            "request_rate": rps,
            "latency": latency,
            "cpu": cpu,
            "replicas": replicas,
        }

        return obs, reward, False, False, info
