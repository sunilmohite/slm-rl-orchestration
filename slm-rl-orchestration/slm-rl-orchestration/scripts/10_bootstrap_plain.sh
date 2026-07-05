#!/usr/bin/env bash
# PATH B: works on any OpenShift cluster with just cluster-admin, no special operators.
# Run from repo root: bash scripts/10_bootstrap_plain.sh <your-github-repo-url>
set -e

REPO_URL=${1:?"Usage: bash scripts/10_bootstrap_plain.sh <github-repo-url>"}
NAMESPACE=slm-rl-demo

echo ">>> Creating namespace"
oc new-project ${NAMESPACE} 2>/dev/null || oc project ${NAMESPACE}

echo ">>> Building + deploying inference service directly from your GitHub repo via S2I"
oc new-app registry.access.redhat.com/ubi8/python-311~${REPO_URL} \
  --context-dir=workload \
  --name=slm-inference \
  -n ${NAMESPACE}

echo ">>> Waiting for build to complete (first build downloads torch/transformers, can take 5-10 min)"
oc logs -f bc/slm-inference -n ${NAMESPACE} || true

echo ">>> Setting resource requests/limits and readiness/liveness probes"
oc set resources deployment/slm-inference -n ${NAMESPACE} \
  --requests=cpu=250m,memory=1Gi --limits=cpu=1,memory=2Gi

oc set probe deployment/slm-inference -n ${NAMESPACE} \
  --readiness --get-url=http://:8080/readyz --initial-delay-seconds=30 --period-seconds=10

oc set probe deployment/slm-inference -n ${NAMESPACE} \
  --liveness --get-url=http://:8080/healthz --initial-delay-seconds=30 --period-seconds=20

echo ">>> Exposing the service externally"
oc expose svc/slm-inference -n ${NAMESPACE}
ROUTE=$(oc get route slm-inference -n ${NAMESPACE} -o jsonpath='{.spec.host}')
echo "Inference endpoint: http://${ROUTE}/generate"

echo ">>> Enabling user workload monitoring (so Prometheus can see our /metrics)"
oc apply -f manifests/enable-user-workload-monitoring.yaml
echo "    (first time only, can take ~1 min for the monitoring operator to reconcile)"
sleep 30

echo ">>> Registering PodMonitor so Prometheus scrapes slm-inference"
PORT_NAME=$(oc get svc slm-inference -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].name}')
sed -i "s/8080-tcp/${PORT_NAME}/" manifests/podmonitor.yaml
oc apply -f manifests/podmonitor.yaml

echo ">>> Applying baseline HPA (for comparison against the RL agent)"
oc apply -f manifests/hpa-baseline.yaml

echo ""
echo "================================================================"
echo " DONE. Test it:"
echo "   curl -X POST http://${ROUTE}/generate -H 'Content-Type: application/json' \\"
echo "        -d '{\"prompt\": \"Kubernetes autoscaling is\", \"max_new_tokens\": 15}'"
echo ""
echo " Prometheus route (create once, for the RL agent to query metrics):"
echo "   oc expose svc thanos-querier -n openshift-monitoring --port=web 2>/dev/null || true"
echo "   oc get route thanos-querier -n openshift-monitoring"
echo "================================================================"
