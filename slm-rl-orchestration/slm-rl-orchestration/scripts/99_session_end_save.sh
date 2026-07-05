#!/usr/bin/env bash
# Run this in the last 5 minutes of EVERY lab session. Non-negotiable.
set -e
cd "$(dirname "$0")/.."

echo ">>> Saving any exported manifests you changed live in the cluster"
mkdir -p manifests/live-snapshot
oc get deployment slm-inference -n slm-rl-demo -o yaml > manifests/live-snapshot/deployment.yaml 2>/dev/null || true
oc get hpa slm-inference-hpa -n slm-rl-demo -o yaml > manifests/live-snapshot/hpa.yaml 2>/dev/null || true

echo ">>> Staging and committing everything"
git add -A
git commit -m "session checkpoint $(date -u +%Y-%m-%dT%H:%M:%SZ)" || echo "nothing new to commit"

echo ">>> Pushing to GitHub"
git push

echo "Done. Safe to let the lab session end/expire now."
