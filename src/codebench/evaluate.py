"""Evaluation metrics for codebench."""

from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

from .core import AgentSubmission, ComplexityScore, ExecutionResult, TestSuite

_INSECURE_PATTERNS: list[tuple[str, str]] = [
    (r"eval\s*\(", "eval"),
    (r"exec\s*\(", "exec"),
    (r"__import__", "__import__"),
    (r"subprocess\.(?:call|run|Popen).*shell\s*=\s*True", "shell=True"),
    (r"os\.system\s*\(", "os.system"),
    (r"pickle\.loads?\s*\(", "pickle.load"),
    (r"yaml\.load\s*\([^,)]+\)", "yaml.load without Loader"),
]


def pass_rate(result: ExecutionResult) -> float:
    """Fraction of tests passed."""
    return result.pass_rate


def regression_rate(result: ExecutionResult) -> float:
    """Fraction of tests that are regressions."""
    return result.regression_count / max(result.tests_total, 1)


def tool_efficiency_score(submission: AgentSubmission, max_tool_calls: int = 20) -> float:
    """Score in [0,1] penalising excessive tool use."""
    return max(0.0, 1.0 - submission.tool_calls_used / max_tool_calls)


def cost_adjusted_score(pr: float, cost_usd: float) -> float:
    """Pass-rate divided by log1p(cost) — rewards cheap solutions."""
    return pr / math.log1p(cost_usd + 1e-9)


def security_score(code: str) -> float:
    """Heuristic security score for generated code.

    Scans for well-known insecure patterns.  Each unique pattern found
    reduces the score by 1/total_patterns.  Returns a value in [0, 1]
    where 1.0 means no insecure patterns detected.
    """
    if not code:
        return 1.0
    findings = sum(
        1 for pattern, _ in _INSECURE_PATTERNS if re.search(pattern, code)
    )
    return max(0.0, 1.0 - findings / len(_INSECURE_PATTERNS))


def functional_correctness_score(suite: TestSuite) -> float:
    """Weighted correctness score across test categories.

    Weights: unit=0.40, integration=0.35, edge_case=0.25.
    Weights are renormalized to only the categories present in the suite,
    so a suite missing a category still scores on a 0-1 scale.
    """
    weights = {"unit": 0.40, "integration": 0.35, "edge_case": 0.25}
    rates = suite.pass_rate_by_category()
    present = {cat: w for cat, w in weights.items() if cat in rates}
    if not present:
        return 0.0
    total_weight = sum(present.values())
    return float(sum(present[cat] * rates[cat] for cat in present) / total_weight)


def complexity_adjusted_score(
    suite: TestSuite,
    complexity: ComplexityScore,
    alpha: float = 0.1,
) -> float:
    """Functional correctness penalised by cyclomatic complexity."""
    base = functional_correctness_score(suite)
    penalty = math.exp(-alpha * max(complexity.cyclomatic_complexity - 1, 0))
    return float(base * penalty)


def agent_summary(
    results: List[ExecutionResult],
    submissions: List[AgentSubmission],
) -> Dict[str, Dict]:
    """Per-agent aggregate statistics."""
    agents: Dict[str, Dict] = {}

    sub_map: Dict[str, List[AgentSubmission]] = {}
    for s in submissions:
        sub_map.setdefault(s.agent_name, []).append(s)

    res_map: Dict[str, List[ExecutionResult]] = {}
    for r in results:
        res_map.setdefault(r.agent_name, []).append(r)

    all_agents = set(sub_map) | set(res_map)
    for agent in all_agents:
        agent_results = res_map.get(agent, [])
        agent_subs = sub_map.get(agent, [])
        n = len(agent_results)
        agents[agent] = {
            "mean_pass_rate": sum(r.pass_rate for r in agent_results) / max(n, 1),
            "mean_regression_rate": sum(regression_rate(r) for r in agent_results) / max(n, 1),
            "mean_latency_ms": sum(s.latency_ms for s in agent_subs) / max(len(agent_subs), 1),
            "mean_cost_usd": sum(s.cost_usd for s in agent_subs) / max(len(agent_subs), 1),
            "n_tasks": n,
        }
    return agents


def leaderboard(
    results: List[ExecutionResult],
    submissions: List[AgentSubmission],
) -> List[Dict]:
    """Sorted leaderboard with pass@1 and pass@5 columns."""
    summary = agent_summary(results, submissions)

    res_map: Dict[str, List[ExecutionResult]] = {}
    for r in results:
        res_map.setdefault(r.agent_name, []).append(r)

    rows = []
    for agent, stats in summary.items():
        agent_results = res_map.get(agent, [])
        rows.append({
            "agent": agent,
            "mean_pass_rate": stats["mean_pass_rate"],
            "pass@1": stats["mean_pass_rate"],
            "pass@5": _estimate_pass_at_k(agent_results, k=5),
            "mean_latency_ms": stats["mean_latency_ms"],
            "mean_cost_usd": stats["mean_cost_usd"],
            "n_tasks": stats["n_tasks"],
        })

    rows.sort(key=lambda x: x["mean_pass_rate"], reverse=True)
    return rows


def _estimate_pass_at_k(results: List[ExecutionResult], k: int) -> float:
    """Average pass@k across tasks using the unbiased estimator."""
    from .core import pass_at_k

    if not results:
        return 0.0
    scores = []
    for r in results:
        scores.append(pass_at_k(max(r.tests_total, k), r.tests_passed, k))
    return sum(scores) / len(scores)


def reliability_at_k(results: List[ExecutionResult], k: int = 5) -> float:
    """Correct operationalization of Chen et al. (2021) pass@k.

    n = independent rollouts per (task, agent)
    c = rollouts where execution_success is True (all tests pass)

    Fixes the category error in _estimate_pass_at_k, which uses tests_total
    and tests_passed (within-submission test counts) instead of rollout counts.
    """
    from .core import pass_at_k

    grouped: Dict[Tuple[str, str], List[ExecutionResult]] = {}
    for r in results:
        grouped.setdefault((r.task_id, r.agent_name), []).append(r)

    scores = []
    for rollouts in grouped.values():
        n = len(rollouts)
        c = sum(1 for r in rollouts if r.execution_success)
        scores.append(pass_at_k(n, c, min(k, n)))
    return sum(scores) / len(scores) if scores else 0.0


def single_rollout_proxy(
    result: ExecutionResult,
    submission: AgentSubmission,
) -> float:
    """Cheap single-rollout proxy for reliability.

    proxy = pass_rate × (1 − regression_rate) × tool_efficiency_score
    Valid as reliability substitute only if Spearman ρ ≥ 0.70 (H3).
    """
    pr = result.pass_rate
    reg = result.regression_count / max(result.tests_total, 1)
    eff = max(0.0, 1.0 - submission.tool_calls_used / 20)
    return pr * (1.0 - reg) * eff


def security_adjusted_reliability_at_k(
    results: List[ExecutionResult],
    submissions: List[AgentSubmission],
    k: int = 5,
    security_threshold: float = 0.80,
) -> float:
    """reliability@k counting only rollouts that are both secure and correct.

    A rollout counts toward c if execution_success is True AND
    security_score(generated_code) >= security_threshold.
    """
    from .core import pass_at_k

    sub_map: Dict[Tuple[str, str], AgentSubmission] = {
        (s.task_id, s.agent_name): s for s in submissions
    }
    grouped: Dict[Tuple[str, str], List[ExecutionResult]] = {}
    for r in results:
        grouped.setdefault((r.task_id, r.agent_name), []).append(r)

    scores = []
    for (task_id, agent_name), rollouts in grouped.items():
        sub = sub_map.get((task_id, agent_name))
        sec = security_score(sub.generated_code) if sub else 1.0
        n = len(rollouts)
        c = sum(1 for r in rollouts if r.execution_success and sec >= security_threshold)
        scores.append(pass_at_k(n, c, min(k, n)))
    return sum(scores) / len(scores) if scores else 0.0
