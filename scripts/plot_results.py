#!/usr/bin/env python3
"""Generate paper figures for all four experiments."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from scipy.stats import spearmanr, pearsonr

from codebench.data import make_benchmark, make_rollout_benchmark
from codebench.evaluate import (
    _estimate_pass_at_k,
    leaderboard,
    reliability_at_k,
    single_rollout_proxy,
)
from codebench.core import ExecutionResult

AGENTS = ["anote-code", "claude-code", "codex"]
SEED = 42
N_TASKS = 10
N_ROLLOUTS = 8
K = 5

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

COLORS = {"pass@1": "#4C72B0", "current": "#DD8452", "reliability": "#55A868", "proxy": "#C44E52"}
plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False})


# ── Figure 1: Baseline artifact ───────────────────────────────────────────────

def fig1_baseline() -> None:
    harness = make_benchmark(n_tasks=N_TASKS, agents=AGENTS, seed=SEED)
    board = leaderboard(harness.results, harness.submissions)

    agents = [r["agent"] for r in board]
    pass1  = [r["pass@1"] for r in board]
    pass5  = [r["pass@5"] for r in board]

    x = np.arange(len(agents))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(x - width / 2, pass1, width, label="Pass@1",           color=COLORS["pass@1"])
    ax.bar(x + width / 2, pass5, width, label="Pass@5 (current)", color=COLORS["current"])

    ax.set_xticks(x)
    ax.set_xticklabels(agents)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score")
    ax.set_title("Figure 1 — Baseline: Pass@1 vs Current Pass@5\n"
                 "(1 submission per task/agent)")
    ax.legend()
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)

    for bar in ax.patches:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig1_baseline.png")
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


# ── Figure 2: H1 category-error proof ────────────────────────────────────────

def fig2_h1_proof() -> None:
    cases = [
        ("Agent-A\n(4/10 tests)", 4, 10),
        ("Agent-B\n(2/5 tests)",  2,  5),
    ]
    labels, values = [], []
    for label, passed, total in cases:
        r = ExecutionResult(
            task_id="probe", agent_name=label.replace("\n", " "),
            tests_passed=passed, tests_total=total,
            regression_count=0, execution_success=True,
        )
        labels.append(label)
        values.append(_estimate_pass_at_k([r], k=K))

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    bars = ax.bar(labels, values, color=[COLORS["current"], COLORS["reliability"]], width=0.4)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel(f"Current pass@{K}")
    ax.set_title("Figure 2 — H1: Category-Error Proof\n"
                 "Same 40% true reliability, different tests_total")

    ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.02,
                f"{val:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.annotate("Identical true\nreliability (40%)\n→ different scores",
                xy=(0.5, min(values) - 0.01), xycoords="data",
                xytext=(0.5, 0.4), textcoords="data",
                ha="center", fontsize=9, color="darkred",
                arrowprops=dict(arrowstyle="-[,widthB=2.5", color="darkred", lw=1.2))

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig2_h1_proof.png")
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


# ── Figure 3: H2 magnitude comparison ────────────────────────────────────────

def fig3_h2_comparison() -> None:
    harness = make_rollout_benchmark(
        n_tasks=N_TASKS, agents=AGENTS, n_rollouts=N_ROLLOUTS, seed=SEED
    )
    by_agent: dict = defaultdict(list)
    for r in harness.results:
        by_agent[r.agent_name].append(r)

    old_vals, new_vals = [], []
    for agent in AGENTS:
        results = by_agent[agent]
        old_vals.append(_estimate_pass_at_k(results, k=K))
        new_vals.append(reliability_at_k(results, k=K))

    x = np.arange(len(AGENTS))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(x - width / 2, old_vals, width, label=f"Current pass@{K} (broken)",      color=COLORS["current"])
    ax.bar(x + width / 2, new_vals, width, label=f"reliability@{K} (corrected)", color=COLORS["reliability"])

    ax.set_xticks(x)
    ax.set_xticklabels(AGENTS)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score")
    ax.set_title(f"Figure 3 — H2: Current pass@{K} vs reliability@{K}\n"
                 f"({N_ROLLOUTS} rollouts/task/agent)")
    ax.legend()
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)

    for bar in ax.patches:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig3_h2_comparison.png")
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


# ── Figure 4: H3 proxy correlation scatter ────────────────────────────────────

def fig4_h3_correlation() -> None:
    harness = make_rollout_benchmark(
        n_tasks=N_TASKS, agents=AGENTS, n_rollouts=N_ROLLOUTS, seed=SEED
    )
    by_task_agent: dict = defaultdict(list)
    for r in harness.results:
        by_task_agent[(r.task_id, r.agent_name)].append(r)
    sub_by_task_agent: dict = defaultdict(list)
    for s in harness.submissions:
        sub_by_task_agent[(s.task_id, s.agent_name)].append(s)

    proxy_scores, rel_scores, agent_labels = [], [], []
    agent_color_map = {a: c for a, c in zip(AGENTS, [COLORS["pass@1"], COLORS["current"], COLORS["reliability"]])}

    for key, rollouts in by_task_agent.items():
        subs = sub_by_task_agent[key]
        if not subs:
            continue
        rel_scores.append(reliability_at_k(rollouts, k=K))
        proxy_scores.append(single_rollout_proxy(rollouts[0], subs[0]))
        agent_labels.append(key[1])

    spearman_r, spearman_p = spearmanr(proxy_scores, rel_scores)
    pearson_r,  pearson_p  = pearsonr(proxy_scores, rel_scores)

    fig, ax = plt.subplots(figsize=(6, 5))
    for agent in AGENTS:
        xs = [proxy_scores[i] for i, a in enumerate(agent_labels) if a == agent]
        ys = [rel_scores[i]   for i, a in enumerate(agent_labels) if a == agent]
        ax.scatter(xs, ys, label=agent, color=agent_color_map[agent], s=60, alpha=0.8)

    # Trend line
    m, b = np.polyfit(proxy_scores, rel_scores, 1)
    x_line = np.linspace(min(proxy_scores), max(proxy_scores), 100)
    ax.plot(x_line, m * x_line + b, color="gray", linestyle="--", linewidth=1.2, alpha=0.7)

    ax.set_xlabel("Single-Rollout Proxy Score")
    ax.set_ylabel(f"reliability@{K}")
    ax.set_title(f"Figure 4 — H3: Proxy vs reliability@{K}\n"
                 f"Spearman ρ = {spearman_r:.3f}  (p = {spearman_p:.3f})")
    ax.legend(fontsize=9)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "fig4_h3_correlation.png")
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close(fig)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fig1_baseline()
    fig2_h1_proof()
    fig3_h2_comparison()
    fig4_h3_correlation()
    print(f"\nAll figures saved to figures/")
