# Adaptive Resource Orchestration for SLM Inference (RL vs HPA)

Everything here runs **inside your DO280 lab workstation** (not the BITS Kubeflow
notebook). The lab gives you a terminal, internet access, and cluster-admin — that's
all you need. GitHub is where your work survives between ephemeral sessions.

## ONE-TIME setup (do this once, from your laptop, before your next lab session)

1. Create a private GitHub repo called `slm-rl-orchestration` (via github.com or `gh repo create`).
2. Generate a GitHub Personal Access Token (classic, `repo` scope) at
   https://github.com/settings/tokens — save it somewhere safe, you'll paste it as your
   git password during lab sessions.
3. Push this folder's contents to that repo:
   ```bash
   cd slm-rl-orchestration
   git init
   git add -A
   git commit -m "initial project skeleton"
   git branch -M main
   git remote add origin https://github.com/<you>/slm-rl-orchestration.git
   git push -u origin main
   ```

## EVERY LAB SESSION — run these in order

### Step 1 — Log into the lab and clone your repo
```bash
oc login https://api.<lab-domain>:6443 -u kubeadmin -p <password> --insecure-skip-tls-verify
git clone https://github.com/<you>/slm-rl-orchestration.git
cd slm-rl-orchestration
```
(If you already cloned it in an earlier session and the workstation persisted, just `git pull` instead.)

### Step 2 — Check what the cluster actually offers
```bash
bash scripts/00_check_environment.sh
```
This tells you whether KServe/Serverless operators are available. For most DO280
lab catalogs they won't be (disconnected/mirrored catalogs are limited to course
content) — that's fine, we use **Path B** below, which needs nothing but a
Deployment/Service, and still gives you the same RL-vs-autoscaling research question.

### Step 3 — Deploy the inference workload
```bash
bash scripts/10_bootstrap_plain.sh https://github.com/<you>/slm-rl-orchestration.git
```
This builds the SLM inference server (from `workload/`) directly from your GitHub
repo using OpenShift's S2I build (no local Docker needed), deploys it, exposes a
Route, turns on monitoring, and applies the baseline HPA.

First build takes 5-10 minutes (downloading PyTorch + transformers). Grab tea.

### Step 4 — Give the RL agent access to Prometheus
```bash
bash scripts/15_setup_prometheus_access.sh
```
Copy the printed `PROMETHEUS_URL` and `PROMETHEUS_TOKEN` into `rl_agent/.env`
(copy `rl_agent/.env.example` to `rl_agent/.env` first — this file is gitignored,
you'll regenerate it fresh each session since the token expires).

### Step 5 — Install Python deps for the RL agent
```bash
cd rl_agent
pip install --user -r requirements.txt
cd ..
```

### Step 6 — Generate traffic (separate terminal tab / background)
```bash
cd workload
pip install --user requests
python load_generator.py --url http://$(oc get route slm-inference -n slm-rl-demo -o jsonpath='{.spec.host}')/generate --pattern spike --duration 900
```
Leave this running in the background (`&` or a second terminal) while you train/evaluate.

### Step 7a — Baseline run: let HPA handle scaling
```bash
oc apply -f manifests/hpa-baseline.yaml   # if not already applied by step 3
cd rl_agent
python evaluate.py --mode hpa --steps 40 --out ../results/hpa_run1.csv
```

### Step 7b — Train the RL agent (delete/disable HPA first so it doesn't fight the agent)
```bash
oc delete hpa slm-inference-hpa -n slm-rl-demo
python train.py --timesteps 2000
```

### Step 8 — Evaluate the trained RL agent under the same traffic pattern
```bash
python evaluate.py --mode rl --model checkpoints/ppo_scaler.zip --steps 40 --out ../results/rl_run1.csv
```

### Step 9 — Compare
Open `results/hpa_run1.csv` and `results/rl_run1.csv` in a notebook or spreadsheet
and plot `p95_latency` and `replicas` over time for each — this is your core
dissertation results chapter.

### Step 10 — ALWAYS run before your session ends
```bash
bash scripts/99_session_end_save.sh
```
This commits and pushes everything (code, checkpoints, results/*.csv) to GitHub.
If your lab expires mid-experiment, you lose nothing except needing to re-run
`scripts/10_bootstrap_plain.sh` next time.

## Repo layout
```
manifests/        # k8s/OpenShift YAML (HPA, PodMonitor, monitoring config)
workload/         # the SLM inference server + load generator
rl_agent/         # Gym env, PPO training, evaluation
scripts/          # numbered — run in order each session
results/          # CSV outputs from evaluate.py, committed to git
```

## If Step 3's S2I build fails
Most common cause: outbound internet blocked for image pulls of `python:3.11`
builder image (should exist in `openshift` imagestream already — check with
`oc get is -n openshift | grep python`). If truly stuck, fall back to
`workload/Dockerfile` and ask for the manual `oc new-build --strategy=docker` variant.
