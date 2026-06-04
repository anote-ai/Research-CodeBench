"""Tests for codebench.core."""

import pytest
from codebench.core import (
    AGENT_NAMES,
    AgentSubmission,
    BenchmarkHarness,
    CodeTask,
    ExecutionResult,
    TaskDifficulty,
    pass_at_k,
)


def _make_task(task_id="t1"):
    return CodeTask(
        task_id=task_id,
        repo="org/repo",
        description="Do the thing.",
        difficulty=TaskDifficulty.EASY,
        test_file="tests/test_foo.py",
        reference_solution="def foo(): pass",
    )


def _make_result(task_id="t1", agent="a", passed=8, total=10):
    return ExecutionResult(
        task_id=task_id,
        agent_name=agent,
        tests_passed=passed,
        tests_total=total,
        execution_success=True,
    )


def test_code_task_construction():
    t = _make_task()
    assert t.task_id == "t1"
    assert t.tags == []


def test_task_difficulty_values():
    assert TaskDifficulty.EASY == "easy"
    assert TaskDifficulty.MEDIUM == "medium"
    assert TaskDifficulty.HARD == "hard"


def test_execution_result_pass_rate():
    r = _make_result(passed=7, total=10)
    assert r.pass_rate == pytest.approx(0.7)


def test_execution_result_pass_rate_zero_total():
    r = _make_result(passed=0, total=0)
    assert r.pass_rate == pytest.approx(0.0)


def test_agent_names_length():
    assert len(AGENT_NAMES) == 5


def test_pass_at_k_in_range():
    value = pass_at_k(10, 5, 1)
    assert 0.0 < value < 1.0


def test_pass_at_k_all_correct():
    assert pass_at_k(10, 10, 3) == pytest.approx(1.0)


def test_pass_at_k_zero_correct():
    assert pass_at_k(10, 0, 1) == pytest.approx(0.0)


def test_benchmark_harness_add_operations():
    harness = BenchmarkHarness()
    task = _make_task()
    result = _make_result()
    sub = AgentSubmission(
        task_id="t1",
        agent_name="a",
        generated_code="pass",
        tool_calls_used=3,
        latency_ms=200.0,
        cost_usd=0.01,
    )
    harness.add_task(task)
    harness.add_submission(sub)
    harness.add_result(result)
    assert len(harness.tasks) == 1
    assert len(harness.submissions) == 1
    assert len(harness.results) == 1


def test_get_results_for_agent():
    harness = BenchmarkHarness()
    harness.add_result(_make_result(agent="alice"))
    harness.add_result(_make_result(agent="bob"))
    assert len(harness.get_results_for_agent("alice")) == 1
    assert len(harness.get_results_for_agent("bob")) == 1
    assert harness.get_results_for_agent("nobody") == []


def test_agent_submission_validation():
    with pytest.raises(Exception):
        AgentSubmission(
            task_id="t1",
            agent_name="a",
            generated_code="pass",
            tool_calls_used=-1,  # invalid
            latency_ms=100.0,
            cost_usd=0.0,
        )
