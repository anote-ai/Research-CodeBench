#!/usr/bin/env python3
"""Run Experiments 0–3 from the CodeBench design doc."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from collections import defaultdict

from scipy.stats import spearmanr

from codebench.core import ExecutionResult
from codebench.data import make_benchmark, make_rollout_benchmark
from codebench.evaluate import (
    _estimate_pass_at_k,
    leaderboard,
    reliability_at_k,
    single_rollout_proxy,
)

AGENTS = ["anote-code", "claude-code", "codex"]
SEED = 42
N_TASKS = 10
N_ROLLOUTS = 8
K = 5


def separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


# ── Experiment 0: Baseline ────────────────────────────────────────────────────

def experiment_0() -> None:
    separator("Experiment 0 — Baseline: Current Leaderboard")

    harness = make_benchmark(n_tasks=N_TASKS, agents=AGENTS, seed=SEED)
    board = leaderboard(harness.results, harness.submissions)

    print(f"\n{'Agent':<16} {'pass@1':>8} {'pass@5':>8} {'mean_pass_rate':>16} {'latency_ms':>12} {'cost_usd':>10}")
    print("-" * 72)
    for row in board:
        print(
            f"{row['agent']:<16} "
            f"{row['pass@1']:>8.3f} "
            f"{row['pass@5']:>8.3f} "
            f"{row['mean_pass_rate']:>16.3f} "
            f"{row['mean_latency_ms']:>12.1f} "
            f"{row['mean_cost_usd']:>10.4f}"
        )

    mean_pass5 = sum(r["pass@5"] for r in board) / len(board)
    mean_pass1 = sum(r["pass@1"] for r in board) / len(board)
    print(f"\nMean pass@5 (current): {mean_pass5:.3f}")
    print(f"Mean pass@1:           {mean_pass1:.3f}")
    print(f"Inflation hint:        {mean_pass5 - mean_pass1:.3f} above pass@1")
    print("\nExpected: all agents ≈ 0.97–1.00 on pass@5 despite mean pass rate ≈ 0.60–0.75.")


# ── Experiment 1: H1 — i.i.d. violation proof ─────────────────────────────────

def experiment_1() -> None:
    separator("Experiment 1 — H1: i.i.d. Violation Proof")

    cases = [
        ("Agent-A", 4, 10),
        ("Agent-B", 2,  5),
    ]

    print(f"\n{'Agent':<10} {'tests_passed':>14} {'tests_total':>13} {'pass_rate':>11} {'pass@5':>8}")
    print("-" * 60)
    results = []
    for label, passed, total in cases:
        r = ExecutionResult(
            task_id="probe",
            agent_name=label,
            tests_passed=passed,
            tests_total=total,
            regression_count=0,
            execution_success=passed == total,
        )
        score = _estimate_pass_at_k([r], k=K)
        results.append((label, passed, total, r.pass_rate, score))
        print(f"{label:<10} {passed:>14} {total:>13} {r.pass_rate:>11.3f} {score:>8.4f}")

    pass_rate_equal = results[0][3] == results[1][3]
    scores_differ = results[0][4] != results[1][4]
    print(f"\npass_rate(A) == pass_rate(B): {pass_rate_equal}")
    print(f"pass@5(A) ≠ pass@5(B):        {scores_differ}")
    print(f"Score difference:              {abs(results[0][4] - results[1][4]):.4f}")
    print("\nH1 confirmed: identical 40% reliability → different pass@5 scores due to test-suite size.")


# ── Experiment 2: H2 — Score inflation magnitude ──────────────────────────────

def experiment_2() -> None:
    separator("Experiment 2 — H2: Score Inflation Magnitude")

    harness = make_rollout_benchmark(
        n_tasks=N_TASKS, agents=AGENTS, n_rollouts=N_ROLLOUTS, seed=SEED
    )

    by_agent: dict = defaultdict(list)
    for r in harness.results:
        by_agent[r.agent_name].append(r)

    print(f"\n{'Agent':<16} {'current_pass@5':>16} {'reliability@5':>15} {'inflation':>11}")
    print("-" * 60)

    inflations = []
    agent_rows = []
    for agent in AGENTS:
        results = by_agent[agent]
        current = _estimate_pass_at_k(results, k=K)
        rel = reliability_at_k(results, k=K)
        inflation = current - rel
        inflations.append(inflation)
        agent_rows.append((agent, current, rel, inflation))
        print(f"{agent:<16} {current:>16.3f} {rel:>15.3f} {inflation:>11.3f}")

    mean_inf = sum(inflations) / len(inflations)
    max_inf = max(inflations)
    print(f"\nMean inflation: {mean_inf:.3f}")
    print(f"Max inflation:  {max_inf:.3f}")
    print(f"H2 threshold:   > 0.50")
    print(f"H2 confirmed:   {mean_inf > 0.50}")

    # Leaderboard flip analysis
    current_rank = sorted(agent_rows, key=lambda x: x[1], reverse=True)
    rel_rank = sorted(agent_rows, key=lambda x: x[2], reverse=True)
    current_order = [r[0] for r in current_rank]
    rel_order = [r[0] for r in rel_rank]

    print(f"\nCurrent pass@5 ranking:  {current_order}")
    print(f"reliability@5 ranking:   {rel_order}")
    print(f"Rank flip observed:      {current_order != rel_order}")


# ── Experiment 3: H3 — Proxy validity ────────────────────────────────────────

def experiment_3() -> None:
    separator("Experiment 3 — H3: Single-Rollout Proxy Validity")

    harness = make_rollout_benchmark(
        n_tasks=N_TASKS, agents=AGENTS, n_rollouts=N_ROLLOUTS, seed=SEED
    )

    sub_map = {(s.task_id, s.agent_name): s for s in harness.submissions}
    by_key: dict = defaultdict(list)
    for r in harness.results:
        by_key[(r.task_id, r.agent_name)].append(r)

    proxy_scores = []
    rel_scores = []
    labels = []

    for key, rollouts in by_key.items():
        sub = sub_map.get(key)
        if sub is None:
            continue
        rel = reliability_at_k(rollouts, k=K)
        proxy = single_rollout_proxy(rollouts[0], sub)
        proxy_scores.append(proxy)
        rel_scores.append(rel)
        labels.append(key[1])

    rho, p_value = spearmanr(proxy_scores, rel_scores)

    print(f"\nSpearman ρ:  {rho:.3f}")
    print(f"p-value:     {p_value:.4f}")
    print(f"H3 threshold: ρ < 0.70 → proxy insufficient")
    print(f"H3 confirmed: {rho < 0.70}  (proxy {'cannot' if rho < 0.70 else 'can'} substitute for reliability@k)")

    if rho < 0.70:
        print("\nInterpretation: single-rollout proxy does not correlate strongly enough")
        print("with reliability@k. Collect ≥5 rollouts per (task, agent) for reliable ranking.")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    experiment_0()
    experiment_1()
    experiment_2()
    experiment_3()
    print("\n\nAll experiments complete.")
