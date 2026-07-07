#!/usr/bin/env bash
# OPTIONAL. Skip this entirely if you don't need dashboard screenshots.
# The RL agent works fine without this -- it talks to Thanos Querier directly.
#
# This deploys a lightweight Grafana instance (community operator or raw
# Deployment, whichever your lab's catalog allows) wired to your existing
# Thanos Querier as a datasource, purely so you can visually demo/screenshot
# request rate, latency, and replica count for your dissertation.
set -e
NAMESPACE=slm-rl-demo

echo ">>> Checking for Grafana Operator in catalog"
if oc get packagemanifests -n openshift-marketplace 2>/dev/null | grep -qi "grafana-operator"; then
  echo "Found Grafana Operator -- installing via OLM is the clean path."
  echo "(Create a Subscription for 'grafana-operator' in namespace ${NAMESPACE}, then a Grafana + GrafanaDatasource CR pointing at thanos-querier. Ask me for the exact YAML if you want to go this route.)"
  exit 0
fi

echo ">>> No Grafana Operator found -- deploying a plain Grafana container instead"
oc new-app grafana/grafana:latest --name=grafana -n ${NAMESPACE}
oc expose svc/grafana -n ${NAMESPACE}

TOKEN=$(oc create token prom-reader -n ${NAMESPACE} --duration=8h 2>/dev/null || true)
ROUTE=$(oc get route thanos-querier -n openshift-monitoring -o jsonpath='{.spec.host}' 2>/dev/null || true)

echo ""
echo "================================================================"
echo " Grafana route:"
oc get route grafana -n ${NAMESPACE} -o jsonpath='{.spec.host}'
echo ""
echo " Add a Prometheus datasource in Grafana's UI pointing to:"
echo "   URL:   https://${ROUTE}"
echo "   Auth:  Bearer Token -> ${TOKEN}"
echo " (Grafana defaults: admin/admin on first login)"
echo "================================================================"
echo ""
echo "Purely cosmetic for your demo -- delete this Deployment any time with:"
echo "  oc delete all -l app=grafana -n ${NAMESPACE}"
