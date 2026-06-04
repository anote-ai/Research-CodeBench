"""Evaluation metrics for codebench."""

from __future__ import annotations

import math
from typing import Dict, List

from .core import AgentSubmission, ExecutionResult


def test_pass_rate(result: ExecutionResult) -> float:
    """Fraction of tests passed."""
    return result.pass_rate


def regression_rate(result: ExecutionResult) -> float:
    """Fraction of tests that are regressions."""
    return result.regression_count / max(result.tests_total, 1)


def tool_efficiency_score(submission: AgentSubmission, max_tool_calls: int = 20) -> float:
    """Score in [0,1] penalising excessive tool use."""
    return max(0.0, 1.0 - submission.tool_calls_used / max_tool_calls)


def cost_adjusted_score(pass_rate: float, cost_usd: float) -> float:
    """Pass-rate divided by log1p(cost) — rewards cheap solutions."""
    return pass_rate / math.log1p(cost_usd + 1e-9)


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
        n = len(agent_results)
        # Treat each task result as one sample; estimate pass@k
        # c = number of results where pass_rate == 1.0
        c = sum(1 for r in agent_results if r.pass_rate >= 1.0)
        rows.append({
            "agent": agent,
            "mean_pass_rate": stats["mean_pass_rate"],
            "pass@1": stats["mean_pass_rate"],  # expectation across tasks
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
        # Treat tests_total as n, tests_passed as c
        scores.append(pass_at_k(max(r.tests_total, k), r.tests_passed, k))
    return sum(scores) / len(scores)
