"""
Trains a PPO agent to scale the SLM inference deployment.

IMPORTANT: run workload/load_generator.py in a separate terminal/session
(or as a background job) WHILE this trains, otherwise there's no traffic
for the agent to learn to react to.

Usage:
  python train.py --timesteps 2000 --step-seconds 15
"""
import argparse
from dotenv import load_dotenv
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from env import SLMScalingEnv

load_dotenv()  # reads PROMETHEUS_URL / PROMETHEUS_TOKEN from rl_agent/.env


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--timesteps", type=int, default=2000)
    p.add_argument("--step-seconds", type=int, default=15)
    p.add_argument("--out", default="checkpoints/ppo_scaler")
    args = p.parse_args()

    env = Monitor(SLMScalingEnv(step_seconds=args.step_seconds))

    model = PPO("MlpPolicy", env, verbose=1, n_steps=64, batch_size=16)
    model.learn(total_timesteps=args.timesteps)

    model.save(args.out)
    print(f"Saved trained policy to {args.out}.zip")
    print("Commit this checkpoint to git before your lab session ends:")
    print(f"  git add {args.out}.zip && git commit -m 'trained policy' && git push")


if __name__ == "__main__":
    main()
