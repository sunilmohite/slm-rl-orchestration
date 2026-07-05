#!/usr/bin/env bash
# Run this FIRST, every session, right after `oc login`.
# It tells you which path to follow: KServe (Path A) or Plain Deployment (Path B).
set -e

echo "================================================================"
echo " Checking cluster identity"
echo "================================================================"
oc whoami
oc cluster-info | head -1

echo ""
echo "================================================================"
echo " Checking for OpenShift Serverless / Service Mesh / RHOAI operators"
echo "================================================================"
echo "--- Serverless ---"
oc get packagemanifests -n openshift-marketplace 2>/dev/null | grep -i serverless || echo "NOT FOUND"

echo "--- Service Mesh ---"
oc get packagemanifests -n openshift-marketplace 2>/dev/null | grep -i "servicemesh\|istio" || echo "NOT FOUND"

echo "--- RHOAI / Open Data Hub (ships KServe) ---"
oc get packagemanifests -n openshift-marketplace 2>/dev/null | grep -i "data-science\|odh\|rhods" || echo "NOT FOUND"

echo "--- cert-manager (needed either way) ---"
oc get packagemanifests -n openshift-marketplace 2>/dev/null | grep -i cert-manager || echo "NOT FOUND"

echo ""
echo "================================================================"
echo " Checking your permissions"
echo "================================================================"
oc auth can-i create subscriptions -n openshift-operators && echo "Can install operators: YES" || echo "Can install operators: NO"
oc auth can-i create namespaces && echo "Can create namespaces: YES" || echo "Can create namespaces: NO"

echo ""
echo "================================================================"
echo " Checking monitoring stack (Prometheus)"
echo "================================================================"
oc get pods -n openshift-monitoring 2>/dev/null | grep prometheus || echo "NOT FOUND / need cluster-monitoring enabled"

echo ""
echo "================================================================"
echo " DECISION GUIDE"
echo "================================================================"
echo "If Serverless + Service Mesh (or RHOAI) show up above -> use Path A (scripts/10_bootstrap_kserve.sh)"
echo "If they DON'T show up, or install fails/times out      -> use Path B (scripts/10_bootstrap_plain.sh)"
echo "Path B still satisfies your thesis goals: it gives you a scalable"
echo "inference workload + real metrics + RL-based scaling vs HPA comparison."
echo "You can mention in your dissertation that KServe's RawDeployment mode"
echo "was targeted but Path B (equivalent Deployment/Service pattern) was used"
echo "due to lab operator-catalog constraints -- this is a normal, honest"
echo "and defensible scoping decision for a time-boxed ephemeral lab."
