"""Tests for TestSuite, ComplexityScore, functional_correctness_score, complexity_adjusted_score."""
from __future__ import annotations

import pytest

from codebench.core import (
    ComplexityScore,
    TestCategory,
    TestResult,
    TestSuite,
)
from codebench.data import make_complexity_score, make_test_suite
from codebench.evaluate import (
    complexity_adjusted_score,
    functional_correctness_score,
)


# ---------------------------------------------------------------------------
# TestSuite
# ---------------------------------------------------------------------------

class TestTestSuite:
    def _suite_all_pass(self) -> TestSuite:
        results = [
            TestResult(test_name="unit_00", category=TestCategory.UNIT, passed=True, execution_time_ms=10.0),
            TestResult(test_name="unit_01", category=TestCategory.UNIT, passed=True, execution_time_ms=15.0),
            TestResult(test_name="int_00", category=TestCategory.INTEGRATION, passed=True, execution_time_ms=30.0),
            TestResult(test_name="edge_00", category=TestCategory.EDGE_CASE, passed=True, execution_time_ms=5.0),
        ]
        return TestSuite(task_id="t001", agent_name="agent-a", test_results=results)

    def _suite_mixed(self) -> TestSuite:
        results = [
            TestResult(test_name="unit_00", category=TestCategory.UNIT, passed=True, execution_time_ms=10.0),
            TestResult(test_name="unit_01", category=TestCategory.UNIT, passed=False, execution_time_ms=12.0),
            TestResult(test_name="int_00", category=TestCategory.INTEGRATION, passed=False, execution_time_ms=25.0),
            TestResult(test_name="edge_00", category=TestCategory.EDGE_CASE, passed=False, execution_time_ms=5.0),
        ]
        return TestSuite(task_id="t002", agent_name="agent-b", test_results=results)

    def test_overall_pass_rate_all_pass(self) -> None:
        suite = self._suite_all_pass()
        assert suite.overall_pass_rate() == pytest.approx(1.0)

    def test_overall_pass_rate_mixed(self) -> None:
        suite = self._suite_mixed()
        assert suite.overall_pass_rate() == pytest.approx(0.25)

    def test_pass_rate_by_category(self) -> None:
        suite = self._suite_mixed()
        rates = suite.pass_rate_by_category()
        assert rates["unit"] == pytest.approx(0.5)
        assert rates["integration"] == pytest.approx(0.0)
        assert rates["edge_case"] == pytest.approx(0.0)

    def test_edge_case_pass_rate(self) -> None:
        suite = self._suite_all_pass()
        assert suite.edge_case_pass_rate() == pytest.approx(1.0)

    def test_total_tests(self) -> None:
        suite = self._suite_all_pass()
        assert suite.total_tests() == 4

    def test_tests_passed(self) -> None:
        suite = self._suite_mixed()
        assert suite.tests_passed() == 1

    def test_empty_suite(self) -> None:
        suite = TestSuite(task_id="t", agent_name="a", test_results=[])
        assert suite.overall_pass_rate() == 0.0
        assert suite.edge_case_pass_rate() == 0.0


# ---------------------------------------------------------------------------
# ComplexityScore
# ---------------------------------------------------------------------------

class TestComplexityScore:
    def test_complexity_rating_low(self) -> None:
        cx = ComplexityScore(task_id="t", agent_name="a", cyclomatic_complexity=3, lines_of_code=20, n_functions=2)
        assert cx.complexity_rating == "low"

    def test_complexity_rating_moderate(self) -> None:
        cx = ComplexityScore(task_id="t", agent_name="a", cyclomatic_complexity=8, lines_of_code=50, n_functions=4)
        assert cx.complexity_rating == "moderate"

    def test_complexity_rating_high(self) -> None:
        cx = ComplexityScore(task_id="t", agent_name="a", cyclomatic_complexity=15, lines_of_code=80, n_functions=5)
        assert cx.complexity_rating == "high"

    def test_complexity_rating_very_high(self) -> None:
        cx = ComplexityScore(task_id="t", agent_name="a", cyclomatic_complexity=25, lines_of_code=200, n_functions=10)
        assert cx.complexity_rating == "very_high"

    def test_average_function_length(self) -> None:
        cx = ComplexityScore(task_id="t", agent_name="a", cyclomatic_complexity=5, lines_of_code=30, n_functions=3)
        assert cx.average_function_length == pytest.approx(10.0)

    def test_make_complexity_score_deterministic(self) -> None:
        cx1 = make_complexity_score("t", "a", seed=7)
        cx2 = make_complexity_score("t", "a", seed=7)
        assert cx1.cyclomatic_complexity == cx2.cyclomatic_complexity


# ---------------------------------------------------------------------------
# functional_correctness_score
# ---------------------------------------------------------------------------

class TestFunctionalCorrectnessScore:
    def test_all_pass_gives_one(self) -> None:
        suite = make_test_suite("t", "a", unit_pass_rate=1.0, integration_pass_rate=1.0, edge_case_pass_rate=1.0, seed=1)
        score = functional_correctness_score(suite)
        assert score == pytest.approx(1.0, abs=0.05)

    def test_all_fail_gives_zero(self) -> None:
        suite = make_test_suite("t", "a", unit_pass_rate=0.0, integration_pass_rate=0.0, edge_case_pass_rate=0.0, seed=2)
        score = functional_correctness_score(suite)
        assert score == pytest.approx(0.0, abs=0.05)

    def test_score_in_range(self) -> None:
        suite = make_test_suite("t", "a", seed=42)
        score = functional_correctness_score(suite)
        assert 0.0 <= score <= 1.0

    def test_edge_case_weight_matters(self) -> None:
        """Suite with poor edge case performance should score lower."""
        suite_good = make_test_suite("t", "a", unit_pass_rate=0.9, integration_pass_rate=0.9, edge_case_pass_rate=0.9, seed=3)
        suite_bad_edge = make_test_suite("t", "a", unit_pass_rate=0.9, integration_pass_rate=0.9, edge_case_pass_rate=0.0, seed=3)
        assert functional_correctness_score(suite_good) > functional_correctness_score(suite_bad_edge)


# ---------------------------------------------------------------------------
# complexity_adjusted_score
# ---------------------------------------------------------------------------

class TestComplexityAdjustedScore:
    def test_lower_complexity_scores_higher(self) -> None:
        suite = make_test_suite("t", "a", unit_pass_rate=1.0, integration_pass_rate=1.0, edge_case_pass_rate=1.0, seed=1)
        cx_simple = ComplexityScore(task_id="t", agent_name="a", cyclomatic_complexity=2, lines_of_code=10, n_functions=1)
        cx_complex = ComplexityScore(task_id="t", agent_name="a", cyclomatic_complexity=20, lines_of_code=100, n_functions=8)
        assert complexity_adjusted_score(suite, cx_simple) > complexity_adjusted_score(suite, cx_complex)

    def test_score_at_most_one(self) -> None:
        suite = make_test_suite("t", "a", unit_pass_rate=1.0, integration_pass_rate=1.0, edge_case_pass_rate=1.0, seed=1)
        cx = ComplexityScore(task_id="t", agent_name="a", cyclomatic_complexity=1, lines_of_code=5, n_functions=1)
        assert complexity_adjusted_score(suite, cx) <= 1.0

    def test_zero_pass_rate_gives_zero(self) -> None:
        suite = make_test_suite("t", "a", unit_pass_rate=0.0, integration_pass_rate=0.0, edge_case_pass_rate=0.0, seed=2)
        cx = ComplexityScore(task_id="t", agent_name="a", cyclomatic_complexity=5, lines_of_code=30, n_functions=3)
        assert complexity_adjusted_score(suite, cx) == pytest.approx(0.0, abs=0.01)
