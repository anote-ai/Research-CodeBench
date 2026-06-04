# CodeBench

> **Benchmarking AI coding agents on real-world repository tasks.**

CodeBench evaluates coding agents on realistic, repo-level Python tasks,
measuring test pass rates, regression rates, tool efficiency, and cost.

## Quickstart

```bash
pip install -e .
python scripts/run_demo.py
```

## Benchmark Design

Each **CodeTask** is drawn from a real or synthetic repository and includes:
- A natural-language `description`
- A `test_file` with unit tests the agent's code must pass
- A `reference_solution` for comparison
- A `difficulty` rating: EASY / MEDIUM / HARD

Agents submit **generated code** along with metadata (tool calls, latency, cost).
An **ExecutionResult** captures how many tests passed and any regressions introduced.

## Eval Metrics

| Metric | Formula | Notes |
|--------|---------|-------|
| Pass Rate | tests_passed / tests_total | Primary metric |
| Pass@k | Unbiased estimator (Chen et al. 2021) | k=1,5,10 |
| Regression Rate | regressions / tests_total | Lower is better |
| Tool Efficiency | max(0, 1 − calls/max_calls) | Rewards concise tool use |
| Cost-Adjusted Score | pass_rate / log1p(cost) | Rewards cheap solutions |

## Agent Comparison Table

| Agent | Pass@1 | Pass@5 | Latency (ms) | Cost (USD) |
|-------|--------|--------|-------------|------------|
| anote-code | — | — | — | — |
| claude-code | — | — | — | — |
| codex | — | — | — | — |
| gemini-code | — | — | — | — |
| copilot | — | — | — | — |

## Venues

- **DAI 2026** — Distributed AI workshop
- **AAAI 2027** — Main track, AI for Software Engineering

## Citation

```bibtex
@misc{codebench2026,
  title   = {CodeBench: A Repository-Level Benchmark for AI Coding Agents},
  author  = {Anote AI},
  year    = {2026},
  url     = {https://github.com/anote-ai/research-codebench}
}
```
