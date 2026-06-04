"""Evaluation metrics for AnoteCodeBench."""

from __future__ import annotations

import math

from codebench.core import AgentSubmission, ExecutionResult


def test_pass_rate(result: ExecutionResult) -> float:
    """Fraction of tests that passed."""
    if result.tests_total == 0:
        return 0.0
    return result.tests_passed / result.tests_total


def regression_rate(result: ExecutionResult) -> float:
    """Fraction of total tests that are regressions."""
    if result.tests_total == 0:
        return 0.0
    return result.regression_count / result.tests_total


def tool_efficiency_score(submission: AgentSubmission, max_tool_calls: int = 20) -> float:
    """Score in [0, 1]: 1 = zero tool calls, 0 = at or beyond max_tool_calls."""
    if max_tool_calls <= 0:
        return 0.0
    used = min(submission.tool_calls_used, max_tool_calls)
    return 1.0 - used / max_tool_calls


def cost_adjusted_score(pass_rate: float, cost_usd: float) -> float:
    """pass_rate divided by log1p(cost_usd)."""
    denominator = math.log1p(cost_usd)
    if denominator == 0.0:
        return 0.0
    return pass_rate / denominator


def leaderboard(
    results: list[ExecutionResult],
    submissions: list[AgentSubmission],
) -> list[dict]:
    """Compute per-agent aggregated metrics, sorted by pass_rate descending."""
    sub_map: dict[tuple[str, str], AgentSubmission] = {
        (s.task_id, s.agent_name): s for s in submissions
    }

    agent_buckets: dict[str, list[dict]] = {}
    for result in results:
        agent = result.agent_name
        pr = test_pass_rate(result)
        rr = regression_rate(result)
        sub = sub_map.get((result.task_id, agent))
        cost = sub.cost_usd if sub else 0.0
        tool_eff = tool_efficiency_score(sub) if sub else 0.0
        agent_buckets.setdefault(agent, []).append(
            {"pass_rate": pr, "regression_rate": rr, "cost_usd": cost, "tool_efficiency": tool_eff}
        )

    rows = []
    for agent, metrics in agent_buckets.items():
        n = len(metrics)
        avg_pass = sum(m["pass_rate"] for m in metrics) / n
        avg_reg = sum(m["regression_rate"] for m in metrics) / n
        avg_cost = sum(m["cost_usd"] for m in metrics) / n
        avg_eff = sum(m["tool_efficiency"] for m in metrics) / n
        rows.append(
            {
                "agent": agent,
                "pass_rate": avg_pass,
                "regression_rate": avg_reg,
                "avg_cost_usd": avg_cost,
                "tool_efficiency": avg_eff,
            }
        )

    rows.sort(key=lambda r: r["pass_rate"], reverse=True)
    return rows
