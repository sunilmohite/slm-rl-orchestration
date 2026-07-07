"""
Plots RL-agent vs HPA runs side by side from the CSVs produced by
rl_agent/evaluate.py. Produces PNGs you can drop straight into the
dissertation's results chapter.

Usage:
  python plot_comparison.py --rl rl_run1.csv --hpa hpa_run1.csv --out comparison.png
"""
import argparse
import csv
import matplotlib.pyplot as plt


def load(path):
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append({k: float(v) for k, v in row.items()})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rl", required=True)
    p.add_argument("--hpa", required=True)
    p.add_argument("--out", default="comparison.png")
    args = p.parse_args()

    rl = load(args.rl)
    hpa = load(args.hpa)

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

    axes[0].plot([r["step"] for r in rl], [r["p95_latency"] for r in rl], label="RL agent")
    axes[0].plot([r["step"] for r in hpa], [r["p95_latency"] for r in hpa], label="HPA")
    axes[0].set_ylabel("p95 latency (s)")
    axes[0].legend()
    axes[0].set_title("Latency: RL agent vs HPA")

    axes[1].plot([r["step"] for r in rl], [r["replicas"] for r in rl], label="RL agent")
    axes[1].plot([r["step"] for r in hpa], [r["replicas"] for r in hpa], label="HPA")
    axes[1].set_ylabel("Replica count")
    axes[1].set_xlabel("Evaluation step")
    axes[1].legend()
    axes[1].set_title("Replica count: RL agent vs HPA")

    plt.tight_layout()
    plt.savefig(args.out, dpi=150)
    print(f"Saved chart to {args.out}")


if __name__ == "__main__":
    main()
