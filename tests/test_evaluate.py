"""Tests for codebench.evaluate."""

import pytest
from codebench.core import AgentSubmission, ExecutionResult
from codebench.evaluate import (
    _estimate_pass_at_k,
    agent_summary,
    cost_adjusted_score,
    leaderboard,
    pass_rate,
    regression_rate,
    security_score,
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


def test_security_score_clean_code():
    code = "def add(a, b):\n    return a + b\n"
    assert security_score(code) == pytest.approx(1.0)


def test_security_score_eval_penalised():
    code = "result = eval(user_input)"
    score = security_score(code)
    assert score < 1.0


def test_security_score_os_system_penalised():
    code = "import os\nos.system('rm -rf /')"
    score = security_score(code)
    assert score < 1.0


def test_security_score_empty_code():
    assert security_score("") == pytest.approx(1.0)


def test_security_score_multiple_issues():
    code = "eval(x); exec(y)"
    score_multi = security_score(code)
    code_single = "eval(x)"
    score_single = security_score(code_single)
    assert score_multi <= score_single


def test_estimate_pass_at_k_conflates_unit_tests_with_rollouts():
    # These two records have the same unit-test pass rate, but the current
    # estimator gives different pass@3 values solely because it treats
    # unit-test counts as sampling counts. True rollout-based pass@k would
    # require independent rollout counts, which these single-run records do
    # not contain.
    case_a = _result(passed=6, total=10)  # 6/10 = 0.6
    case_b = _result(passed=3, total=5)   # 3/5  = 0.6

    assert case_a.pass_rate == pytest.approx(case_b.pass_rate)

    # Current (incorrect) behavior: treats unit-test counts as sample counts.
    # pass_at_k(10, 6, 3) = 1 - C(4,3)/C(10,3) = 1 - 4/120 ≈ 0.9667
    # pass_at_k(5,  3, 3) = 1.0  (n-c=2 < k=3, early exit)
    pa = _estimate_pass_at_k([case_a], k=3)
    pb = _estimate_pass_at_k([case_b], k=3)

    assert pa == pytest.approx(0.9666667, abs=1e-6)
    assert pb == pytest.approx(1.0)
    assert pa < pb  # documents the category error
