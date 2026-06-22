"""Tests for codebench.data."""

import pytest
from collections import Counter
from codebench.data import SAMPLE_TASKS, make_benchmark, make_rollout_benchmark, make_submission, make_task
from codebench.core import BenchmarkHarness, CodeTask


def test_sample_tasks_length():
    assert len(SAMPLE_TASKS) == 10


def test_make_task_returns_code_task():
    t = make_task(0)
    assert isinstance(t, CodeTask)
    assert t.task_id == "task-001"


def test_make_submission_structure():
    sub, res = make_submission("t1", pass_rate=0.9)
    assert sub.task_id == "t1"
    assert res.task_id == "t1"
    assert res.tests_passed == 9


def test_make_benchmark_returns_harness():
    h = make_benchmark(n_tasks=5, agents=["a", "b"])
    assert isinstance(h, BenchmarkHarness)
    assert len(h.tasks) == 5
    assert len(h.results) == 10  # 5 tasks * 2 agents


def test_make_rollout_benchmark_returns_harness():
    h = make_rollout_benchmark(n_tasks=2, agents=["a"], n_rollouts=3)
    assert isinstance(h, BenchmarkHarness)


def test_make_rollout_benchmark_result_count():
    h = make_rollout_benchmark(n_tasks=3, agents=["a", "b"], n_rollouts=4)
    assert len(h.results) == 3 * 2 * 4  # 24


def test_make_rollout_benchmark_grouping():
    n_rollouts = 4
    h = make_rollout_benchmark(n_tasks=3, agents=["a", "b"], n_rollouts=n_rollouts)
    counts = Counter((r.task_id, r.agent_name) for r in h.results)
    assert len(counts) == 3 * 2  # all (task, agent) pairs present
    assert all(c == n_rollouts for c in counts.values())


def test_make_rollout_benchmark_reproducible():
    kwargs = dict(n_tasks=3, agents=["a", "b"], n_rollouts=5, seed=99)
    h1 = make_rollout_benchmark(**kwargs)
    h2 = make_rollout_benchmark(**kwargs)

    def to_tuples(h):
        return [
            (r.task_id, r.agent_name, r.tests_passed, r.tests_total,
             r.regression_count, r.execution_success)
            for r in h.results
        ]

    assert to_tuples(h1) == to_tuples(h2)


@pytest.mark.parametrize("bad", [0, -1])
def test_make_rollout_benchmark_invalid_n_rollouts(bad):
    with pytest.raises(ValueError):
        make_rollout_benchmark(n_rollouts=bad)


def test_make_rollout_benchmark_execution_success_semantics():
    # execution_success must mean "all tests passed", not "any test passed"
    h = make_rollout_benchmark(n_tasks=3, agents=["a", "b"], n_rollouts=10, seed=42)
    for r in h.results:
        assert r.execution_success == (r.tests_passed == r.tests_total)


def test_make_rollout_benchmark_variation():
    # p is drawn from [0.3, 0.95]; with a fixed seed and 50 rollouts, tests_passed must vary.
    h = make_rollout_benchmark(n_tasks=1, agents=["a"], n_rollouts=50, seed=7)
    passed_counts = [r.tests_passed for r in h.results]
    assert len(set(passed_counts)) > 1
