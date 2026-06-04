"""Tests for codebench.evaluate."""

import pytest
from codebench.core import AgentSubmission, ExecutionResult
from codebench.evaluate import (
    agent_summary,
    cost_adjusted_score,
    leaderboard,
    pass_rate,
    regression_rate,
    tool_efficiency_score,
)


def _result(passed=8, total=10, reg=1, agent="a", task="t1"):
    return ExecutionResult(
        task_id=task,
        agent_name=agent,
        tests_passed=passed,
        tests_total=total,
        regression_count=reg,
        execution_success=True,
    )


def _sub(agent="a", task="t1", tool_calls=5, latency=500.0, cost=0.01):
    return AgentSubmission(
        task_id=task,
        agent_name=agent,
        generated_code="pass",
        tool_calls_used=tool_calls,
        latency_ms=latency,
        cost_usd=cost,
    )


def test_test_pass_rate():
    r = _result(passed=8, total=10)
    assert pass_rate(r) == pytest.approx(0.8)


def test_regression_rate():
    r = _result(reg=2, total=10)
    assert regression_rate(r) == pytest.approx(0.2)


def test_tool_efficiency_score_at_max():
    s = _sub(tool_calls=20)
    assert tool_efficiency_score(s, max_tool_calls=20) == pytest.approx(0.0)


def test_tool_efficiency_score_over_budget():
    s = _sub(tool_calls=25)
    assert tool_efficiency_score(s, max_tool_calls=20) == pytest.approx(0.0)


def test_cost_adjusted_score():
    val = cost_adjusted_score(1.0, 0.0)
    assert val > 0


def test_agent_summary_structure():
    results = [_result(agent="a"), _result(agent="b")]
    subs = [_sub(agent="a"), _sub(agent="b")]
    summary = agent_summary(results, subs)
    assert "a" in summary
    assert "mean_pass_rate" in summary["a"]
    assert "n_tasks" in summary["a"]


def test_leaderboard_sorted_descending():
    results = [
        _result(passed=10, total=10, agent="best"),
        _result(passed=2, total=10, agent="worst"),
    ]
    subs = [_sub(agent="best"), _sub(agent="worst")]
    board = leaderboard(results, subs)
    assert board[0]["agent"] == "best"
    assert board[0]["mean_pass_rate"] >= board[1]["mean_pass_rate"]
