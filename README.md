# AnoteCodeBench

> Benchmarking Enterprise Code-Generation Agents vs. Claude Code & Codex

AnoteCodeBench is a SWE-bench / terminal-bench-style evaluation framework that measures code-generation agents on **repo-level programming tasks** with an emphasis on enterprise private-repository scenarios.

---

## Benchmark Design

### Task Categories

| Category | Description |
|----------|-------------|
| Bug Fix | Identify and fix a regression introduced in a commit |
| Feature Implementation | Implement a new function/class from a docstring spec |
| Refactoring | Restructure existing code without changing behaviour |
| Test Writing | Write a test suite for a provided module |
| Documentation | Generate accurate docstrings and README sections |

### Difficulty Levels

| Level | Criteria |
|-------|----------|
| EASY | Single-file changes, clear specification |
| MEDIUM | Multi-file changes, moderate ambiguity |
| HARD | Cross-repo dependencies, underspecified requirements |

---

## Agent Comparison

| Agent | pass@1 | pass@5 | Regression Rate | Avg Cost (USD) |
|-------|--------|--------|-----------------|----------------|
| anote-code | 0.61 | 0.84 | 0.04 | 0.08 |
| claude-code | 0.59 | 0.81 | 0.03 | 0.12 |
| codex | 0.53 | 0.76 | 0.06 | 0.07 |
| gemini-code | 0.50 | 0.72 | 0.07 | 0.09 |
| copilot | 0.47 | 0.69 | 0.08 | 0.05 |

*Results are illustrative placeholders; run the benchmark to obtain real numbers.*

---

## Evaluation Metrics

- **pass@k** — Unbiased estimator `1 - C(n-c,k)/C(n,k)` (Chen et al., 2021)
- **test_pass_rate** — Fraction of unit tests that pass for a given submission
- **regression_rate** — Fraction of previously-passing tests broken by the submission
- **tool_efficiency_score** — Penalises excessive tool calls (normalised to [0,1])
- **cost_adjusted_score** — `pass_rate / log1p(cost_usd)` for cost-aware ranking

---

## Quickstart

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

```python
from codebench.core import CodeTask, TaskDifficulty, pass_at_k
from codebench.evaluate import leaderboard

# Compute pass@3 given 10 samples, 5 correct
print(pass_at_k(n=10, c=5, k=3))
```

---

## Citation

```bibtex
@misc{anote2024codebench,
  title  = {AnoteCodeBench: Benchmarking Enterprise Code-Generation Agents},
  author = {Anote AI},
  year   = {2024},
  url    = {https://github.com/anote-ai/research-codebench}
}
```
