#!/usr/bin/env bash
# OpenShift's built-in Prometheus (thanos-querier) sits behind OAuth.
# This creates a service account with cluster-monitoring-view rights and
# prints a token + route your RL agent will use to query metrics.
set -e
NAMESPACE=slm-rl-demo

oc create sa prom-reader -n ${NAMESPACE} 2>/dev/null || true
oc adm policy add-cluster-role-to-user cluster-monitoring-view \
  -z prom-reader -n ${NAMESPACE}

echo ">>> Exposing thanos-querier route (idempotent)"
oc expose svc thanos-querier -n openshift-monitoring --port=web 2>/dev/null || true
ROUTE=$(oc get route thanos-querier -n openshift-monitoring -o jsonpath='{.spec.host}')

TOKEN=$(oc create token prom-reader -n ${NAMESPACE} --duration=8h)

echo ""
echo "================================================================"
echo " Put these into rl_agent/.env (create the file, don't commit it):"
echo ""
echo "PROMETHEUS_URL=https://${ROUTE}"
echo "PROMETHEUS_TOKEN=${TOKEN}"
echo ""
echo " NOTE: token expires in 8h (typically your whole lab session)."
echo " Re-run this script if it expires or you start a new session."
echo "================================================================"
