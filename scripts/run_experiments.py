#!/usr/bin/env python3
"""Run all three reliability@k experiments and print results.

Experiment 0 — Baseline: current pass@k leaderboard (one submission/task/agent).
Experiment 1 — H1 proof: two agents with identical true reliability but different
               tests_total yield different current pass@k.
Experiment 2 — H2 comparison: reliability@k (multi-rollout) vs current pass@k.
Experiment 3 — H3 proxy correlation: single-rollout proxy vs reliability@k.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from collections import defaultdict
from scipy.stats import spearmanr, pearsonr

from codebench.data import make_benchmark, make_rollout_benchmark
from codebench.evaluate import (
    _estimate_pass_at_k,
    leaderboard,
    reliability_at_k,
    single_rollout_proxy,
)
from codebench.core import ExecutionResult

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

AGENTS = ["anote-code", "claude-code", "codex"]
SEED = 42
N_TASKS = 10
N_ROLLOUTS = 8
K = 5

SEP = "\n" + "=" * 65 + "\n"


def section(title: str) -> None:
    if HAS_RICH:
        console.rule(f"[bold cyan]{title}[/bold cyan]")
    else:
        print(SEP + title + SEP)


# ── Experiment 0 ─────────────────────────────────────────────────────────────

def exp0_baseline() -> None:
    section("Experiment 0 — Baseline (current pass@k, 1 submission/task/agent)")
    harness = make_benchmark(n_tasks=N_TASKS, agents=AGENTS, seed=SEED)
    board = leaderboard(harness.results, harness.submissions)

    if HAS_RICH:
        t = Table(title="Baseline Leaderboard")
        for col, justify in [("Rank", "right"), ("Agent", "left"),
                              ("Pass@1", "right"), (f"Pass@{K} (current)", "right")]:
            t.add_column(col, justify=justify)
        for rank, row in enumerate(board, 1):
            t.add_row(str(rank), row["agent"],
                      f"{row['pass@1']:.3f}", f"{row['pass@5']:.3f}")
        console.print(t)
    else:
        print(f"{'Rank':>4}  {'Agent':<14}  {'Pass@1':>8}  {f'Pass@{K} (current)':>18}")
        for rank, row in enumerate(board, 1):
            print(f"{rank:>4}  {row['agent']:<14}  {row['pass@1']:>8.3f}  {row['pass@5']:>18.3f}")

    print("\nObservation: Pass@5 saturates near 1.0 despite Pass@1 ~ 0.60-0.64.")
    print("This is the artifact that Experiments 1-3 diagnose and fix.\n")


# ── Experiment 1 ─────────────────────────────────────────────────────────────

def exp1_h1_proof() -> None:
    section("Experiment 1 — H1: Category-Error Proof")

    cases = [
        ("Agent-A (4/10 tests)", 4, 10),
        ("Agent-B (2/5 tests)",  2,  5),
    ]
    print("Both agents have identical true reliability: 40% per-attempt pass rate.")
    print("Only tests_total differs (10 vs 5).\n")
    print(f"{'Agent':<24}  {'tests_passed/total':>18}  {f'Current pass@{K}':>16}")
    print("-" * 62)
    values = []
    for label, passed, total in cases:
        r = ExecutionResult(
            task_id="probe", agent_name=label,
            tests_passed=passed, tests_total=total,
            regression_count=0, execution_success=True,
        )
        pk = _estimate_pass_at_k([r], k=K)
        values.append(pk)
        print(f"{label:<24}  {f'{passed}/{total}':>18}  {pk:>16.4f}")

    print()
    diff = abs(values[0] - values[1])
    if diff > 1e-6:
        print(f"H1 CONFIRMED — pass@{K} differs by {diff:.4f} for agents with")
        print("identical true reliability. The formula is driven by tests_total,")
        print("not by actual agent behavior.\n")
    else:
        print(f"H1 NOT confirmed: values are equal ({values[0]:.4f}).\n")


# ── Experiment 2 ─────────────────────────────────────────────────────────────

def exp2_h2_comparison() -> None:
    section(f"Experiment 2 — H2: reliability@{K} vs current pass@{K} ({N_ROLLOUTS} rollouts/task/agent)")

    harness = make_rollout_benchmark(
        n_tasks=N_TASKS, agents=AGENTS, n_rollouts=N_ROLLOUTS, seed=SEED
    )

    by_agent: dict = defaultdict(list)
    for r in harness.results:
        by_agent[r.agent_name].append(r)

    rows = []
    for agent in AGENTS:
        results = by_agent[agent]
        old_pk = _estimate_pass_at_k(results, k=K)
        new_pk = reliability_at_k(results, k=K)
        rows.append((agent, old_pk, new_pk))

    if HAS_RICH:
        t = Table(title=f"Current pass@{K} vs reliability@{K}")
        t.add_column("Agent")
        t.add_column(f"Current pass@{K} (broken)", justify="right")
        t.add_column(f"reliability@{K} (corrected)", justify="right")
        t.add_column("Δ", justify="right")
        for agent, old, new in rows:
            t.add_row(agent, f"{old:.3f}", f"{new:.3f}", f"{new - old:+.3f}")
        console.print(t)
    else:
        print(f"{'Agent':<14}  {f'Current pass@{K}':>20}  {f'reliability@{K}':>20}  {'Δ':>8}")
        print("-" * 68)
        for agent, old, new in rows:
            print(f"{agent:<14}  {old:>20.3f}  {new:>20.3f}  {new - old:>+8.3f}")

    old_rank = [r[0] for r in sorted(rows, key=lambda x: -x[1])]
    new_rank = [r[0] for r in sorted(rows, key=lambda x: -x[2])]
    print(f"\nCurrent pass@{K} ranking:  {' > '.join(old_rank)}")
    print(f"reliability@{K} ranking:   {' > '.join(new_rank)}")
    if old_rank != new_rank:
        print(f"\nH2 CONFIRMED — rankings diverge between the two metrics.\n")
    else:
        print(f"\nH2 PARTIAL — same ranking order, but magnitudes still differ.\n")


# ── Experiment 3 ─────────────────────────────────────────────────────────────

def exp3_h3_proxy() -> None:
    section("Experiment 3 — H3: Single-Rollout Proxy Correlation with reliability@k")

    harness = make_rollout_benchmark(
        n_tasks=N_TASKS, agents=AGENTS, n_rollouts=N_ROLLOUTS, seed=SEED
    )

    by_task_agent: dict = defaultdict(list)
    for r in harness.results:
        by_task_agent[(r.task_id, r.agent_name)].append(r)

    sub_by_task_agent: dict = defaultdict(list)
    for s in harness.submissions:
        sub_by_task_agent[(s.task_id, s.agent_name)].append(s)

    proxy_scores = []
    rel_scores = []

    for key, rollouts in by_task_agent.items():
        subs = sub_by_task_agent[key]
        if not subs:
            continue
        rel = reliability_at_k(rollouts, k=K)
        proxy = single_rollout_proxy(rollouts[0], subs[0])
        proxy_scores.append(proxy)
        rel_scores.append(rel)

    spearman_r, spearman_p = spearmanr(proxy_scores, rel_scores)
    pearson_r, pearson_p = pearsonr(proxy_scores, rel_scores)

    print(f"n = {len(proxy_scores)} (task, agent) pairs\n")
    print(f"  Spearman ρ = {spearman_r:+.3f}  (p = {spearman_p:.3f})")
    print(f"  Pearson  r = {pearson_r:+.3f}  (p = {pearson_p:.3f})\n")

    if abs(spearman_r) >= 0.5:
        print("H3 SUPPORTED — moderate-to-strong correlation.")
        print("Single-rollout proxy partially tracks reliability@k.\n")
    else:
        print("H3 NOT SUPPORTED — weak correlation.")
        print("A single rollout cannot substitute for reliability@k.\n")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    exp0_baseline()
    exp1_h1_proof()
    exp2_h2_comparison()
    exp3_h3_proxy()
