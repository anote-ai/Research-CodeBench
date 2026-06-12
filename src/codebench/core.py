"""Core data models and utilities for AnoteCodeBench."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from pydantic import BaseModel, Field


class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CodeTask(BaseModel):
    task_id: str
    repo: str
    description: str
    difficulty: TaskDifficulty
    test_file: str
    reference_solution: str


class AgentSubmission(BaseModel):
    task_id: str
    agent_name: str
    generated_code: str
    tool_calls_used: int = Field(ge=0)
    latency_ms: float = Field(ge=0.0)
    cost_usd: float = Field(ge=0.0)


class ExecutionResult(BaseModel):
    task_id: str
    agent_name: str
    tests_passed: int = Field(ge=0)
    tests_total: int = Field(ge=0)
    regression_count: int = Field(ge=0)
    execution_success: bool

    @property
    def pass_rate(self) -> float:
        """Fraction of tests passed."""
        return self.tests_passed / max(self.tests_total, 1)


@dataclass
class ComplexityScore:
    """Cyclomatic and cognitive complexity scores for a code submission."""

    task_id: str
    cyclomatic_complexity: float = 1.0
    cognitive_complexity: float = 1.0


@dataclass
class TestSuite:
    """Aggregated test results broken down by category."""

    task_id: str
    results_by_category: Dict[str, ExecutionResult] = field(default_factory=dict)

    def pass_rate_by_category(self) -> Dict[str, float]:
        """Return pass rate per category."""
        return {
            cat: result.pass_rate
            for cat, result in self.results_by_category.items()
        }


AGENT_NAMES: list[str] = [
    "anote-code",
    "claude-code",
    "codex",
    "gemini-code",
    "copilot",
]


def _comb(n: int, k: int) -> float:
    """Return C(n, k) as a float, returning 0.0 if k > n."""
    if k > n:
        return 0.0
    return float(math.comb(n, k))


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k estimator: 1 - C(n-c, k) / C(n, k).

    Args:
        n: total number of samples generated.
        c: number of correct samples.
        k: k in pass@k.

    Returns:
        Estimated probability that at least one of k samples passes.
    """
    if n == 0 or k > n:
        return 0.0
    denom = _comb(n, k)
    if denom == 0.0:
        return 0.0
    numer = _comb(n - c, k)
    return 1.0 - numer / denom
