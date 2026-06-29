# CodeBench

> **Benchmarking AI coding agents on real-world repository tasks.**

CodeBench evaluates coding agents on realistic, repo-level Python tasks,
measuring test pass rates, regression rates, tool efficiency, and cost.

## Project documents

- [DESIGN_DOC.md](./DESIGN_DOC.md) — full research design: novelty claims,
  experiments, metrics (SSR/SGR/CIR), and timeline.
- [PAPER_DRAFT.md](./PAPER_DRAFT.md) — paper-skeleton tracking which
  numbers are measured vs. projected/hypothesized.
- [BLOG.md](./BLOG.md) — plain-language summary for a non-academic
  audience, including an honest status update on what's implemented.
- [results/README.md](./results/README.md) — what's in `results/` and
  what is intentionally not there yet.

## Quickstart

```bash
pip install -e .
python scripts/run_demo.py
```

The demo above uses **synthetic, seeded-random data** (see
`src/codebench/data.py::make_benchmark`) to validate the scoring pipeline.
It is not a real evaluation of any coding agent.

For a baseline experiment that actually executes real code (the 10 sample
tasks' reference solutions) rather than drawing from a random number
generator, run:

```bash
python experiments/exp0_baseline.py
```

See the `experiments/exp0_baseline.py` module docstring and
`results/README.md` for exactly what this does and does not prove.

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

This table is intentionally empty: no real agent has been run against a
real task set yet. See `experiments/exp0_baseline.py` for the first script
that executes real code, and `PAPER_DRAFT.md` for the plan to populate this
table with measured (not projected) numbers.

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
