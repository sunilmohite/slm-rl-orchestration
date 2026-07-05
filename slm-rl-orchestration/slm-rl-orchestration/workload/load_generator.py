"""
Traffic generator for experiments. Produces steady, ramping, or spiky load
against the /generate endpoint so you can compare HPA vs RL-agent scaling.

Usage:
  python load_generator.py --url http://<route>/generate --pattern spike --duration 600
"""
import argparse
import time
import random
import threading
import requests

PROMPTS = [
    "The future of cloud computing is",
    "Kubernetes autoscaling helps because",
    "Reinforcement learning agents can",
    "Small language models are useful when",
]


def send_request(url):
    try:
        requests.post(
            url,
            json={"prompt": random.choice(PROMPTS), "max_new_tokens": 20},
            timeout=15,
        )
    except requests.RequestException as e:
        print(f"request failed: {e}")


def rate_for_pattern(pattern, t, duration):
    """Returns requests-per-second target at time t (seconds since start)."""
    frac = t / duration
    if pattern == "steady":
        return 3
    if pattern == "ramp":
        return 1 + frac * 9  # 1 -> 10 rps
    if pattern == "spike":
        # quiet, then a sharp spike in the middle third, then quiet again
        if 0.4 < frac < 0.6:
            return 15
        return 2
    if pattern == "diurnal":
        import math
        return 5 + 5 * math.sin(2 * math.pi * frac)
    return 3


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--pattern", choices=["steady", "ramp", "spike", "diurnal"], default="steady")
    p.add_argument("--duration", type=int, default=300, help="seconds")
    args = p.parse_args()

    start = time.time()
    while time.time() - start < args.duration:
        t = time.time() - start
        rps = max(0.2, rate_for_pattern(args.pattern, t, args.duration))
        n = max(1, int(rps))
        for _ in range(n):
            threading.Thread(target=send_request, args=(args.url,), daemon=True).start()
        print(f"t={t:.0f}s pattern={args.pattern} target_rps={rps:.1f}")
        time.sleep(1)


if __name__ == "__main__":
    main()
