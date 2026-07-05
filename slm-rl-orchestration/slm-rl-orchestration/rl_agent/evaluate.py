"""
Runs an evaluation episode and logs metrics to CSV so you can plot
RL-agent vs HPA behavior side by side for your dissertation results chapter.

Usage:
  # RL agent controls scaling (make sure HPA is deleted/disabled first!):
  python evaluate.py --mode rl --model checkpoints/ppo_scaler.zip --steps 40 --out ../results/rl_run1.csv

  # HPA controls scaling (just observe, agent takes no actions):
  python evaluate.py --mode hpa --steps 40 --out ../results/hpa_run1.csv
"""
import argparse
import csv
import time
from dotenv import load_dotenv
from stable_baselines3 import PPO
from env import SLMScalingEnv

load_dotenv()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["rl", "hpa"], required=True)
    p.add_argument("--model", default="checkpoints/ppo_scaler.zip")
    p.add_argument("--steps", type=int, default=40)
    p.add_argument("--step-seconds", type=int, default=15)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    env = SLMScalingEnv(step_seconds=args.step_seconds)
    obs, _ = env.reset()

    model = PPO.load(args.model) if args.mode == "rl" else None

    rows = []
    for i in range(args.steps):
        if args.mode == "rl":
            action, _ = model.predict(obs, deterministic=True)
        else:
            action = 1  # no-op: let HPA (applied separately via oc apply) do the scaling

        obs, reward, terminated, truncated, info = env.step(int(action))
        row = {"step": i, "time": time.time(), "reward": reward, **info}
        rows.append(row)
        print(row)

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
