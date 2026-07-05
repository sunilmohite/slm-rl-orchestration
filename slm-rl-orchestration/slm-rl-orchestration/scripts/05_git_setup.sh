#!/usr/bin/env bash
# Run ONCE, first time you ever set this repo up (on your laptop, to create
# the repo), and again inside the DO280 workstation each session to clone it.
set -e

echo "=== ONE-TIME: create the GitHub repo (do this on GitHub.com, or via gh CLI) ==="
echo "gh repo create slm-rl-orchestration --private --confirm"
echo ""
echo "=== EVERY SESSION on the DO280 workstation: clone it ==="
echo "git clone https://github.com/<you>/slm-rl-orchestration.git"
echo "cd slm-rl-orchestration"
echo ""
echo "=== Configure identity (only needed once per fresh workstation) ==="
echo "git config --global user.name \"Your Name\""
echo "git config --global user.email \"you@example.com\""
echo ""
echo "=== Auth: use a Personal Access Token (classic, repo scope) as your password ==="
echo "When git asks for a password on 'git push', paste your PAT, not your GitHub password."
echo "Generate one at: https://github.com/settings/tokens"
echo ""
echo "=== To avoid retyping the PAT every push during a session ==="
echo "git config --global credential.helper 'cache --timeout=28800'   # 8 hours"
