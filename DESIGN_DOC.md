# Research Design Document: Reliability@k for Agentic Code Generation

## Vision Statement

Establish a **valid reliability metric for agentic coding benchmarks**: replace CodeBench's
current `pass@k` — which silently misapplies the Chen et al. (2021) estimator to
within-attempt unit-test counts — with a metric that actually answers the question
practitioners care about: *"If I run this agent on a similar task again, how likely is it
to produce a fully working solution?"*

---

## Problem Statement & Novelty

`pass@k` was designed for **sampling-based code completion** (HumanEval, MBPP): generate
`n` independent full-solution samples for a problem, count `c` that are fully correct, and
estimate the probability that at least one of `k` randomly drawn samples is correct.

CodeBench's current implementation (`_estimate_pass_at_k` in
[`src/codebench/evaluate.py`](src/codebench/evaluate.py)) instead computes:

```python
pass_at_k(n=max(tests_total, k), c=tests_passed, k=k)
```

This substitutes `tests_total`/`tests_passed` — the number of **unit tests within a single
submission** — for `n`/`c`, the number of **independent full-solution attempts**. These are
not the same quantity. Agentic coding tools (Claude Code, Codex, Copilot, etc.) are run
**once per task**, not sampled `n` times, so the formula's core assumption never holds.

### Observed Effect (Baseline Run)

Running the existing `make_benchmark()` + `leaderboard()` on the 10-task synthetic
benchmark produces:

| Rank | Agent | Pass@1 | Pass@5 |
|---|---|---|---|
| 1 | anote-code | 0.640 | 0.993 |
| 2 | claude-code | 0.600 | 0.975 |
| 3 | codex | 0.600 | 0.992 |

Pass@5 jumps to ~0.97–0.99 for *every* agent regardless of Pass@1, because `n=10`
(`tests_total`) makes the combinatorial estimator nearly saturate at `k=5`. This number
does not reflect "5 independent tries" — no such tries occurred.

### Novel Contributions

| Contribution | Description |
|---|---|
| **Category-error proof** | Constructed counter-example showing two agents with identical "true" reliability but different `tests_total` yield different `pass@k` under the current formula |
| **`reliability@k` metric** | Corrected estimator: `n` = number of independent rollouts per task, `c` = number of rollouts with `execution_success = True` |
| **Rollout generator** | Extension to `data.py` producing `n` independent `AgentSubmission`/`ExecutionResult` pairs per `(task, agent)`, with per-rollout variance |
| **Cheap-proxy analysis** | Correlation study testing whether a single-rollout signal (`functional_correctness_score`, `regression_rate`, `tool_calls_used`) approximates `reliability@k` |

---

## Research Objectives

1. **Diagnose**: Prove the current `pass@k` is a category error, not a minor calibration issue.
2. **Define**: Implement `reliability_at_k`, correctly parameterized from repeated rollouts.
3. **Compare**: Quantify how much current `pass@k` and `reliability@k` diverge in ranking and magnitude.
4. **Reduce cost**: Determine whether a single-rollout proxy can approximate `reliability@k`
   well enough to avoid the cost of repeated agent runs.

---

## Systems Under Evaluation

| Agent | Source | Notes |
|---|---|---|
| anote-code | `AGENT_NAMES` (`core.py`) | Currently synthetic data only |
| claude-code | `AGENT_NAMES` (`core.py`) | Currently synthetic data only |
| codex | `AGENT_NAMES` (`core.py`) | Currently synthetic data only |
| gemini-code | `AGENT_NAMES` (`core.py`) | Not yet exercised in `make_benchmark` |
| copilot | `AGENT_NAMES` (`core.py`) | Not yet exercised in `make_benchmark` |

All experiments below use CodeBench's existing 10-task synthetic suite
(`SAMPLE_TASKS` in [`data.py`](src/codebench/data.py)) with simulated rollouts; the design
generalizes directly to real agent traces if/when available.

---

## Experimental Design

### Baseline Experiment (Experiment 0)
**Protocol**: Run `make_benchmark()` unmodified (one submission per task/agent) and report
the current `pass@1`/`pass@5` from `leaderboard()`.

**Result**: see table above — already run. This is the status-quo leaderboard teams would
currently see.

---

### Experiment 1: Category-Error Proof (H1)
**Hypothesis (H1)**: Current `pass@k` does not track true reliability — two agents with
identical repeat-success rates but different `tests_total` will show different `pass@k`.

**Protocol**:
1. Construct two synthetic `ExecutionResult`s with the same `tests_passed / tests_total`
   ratio (e.g., 6/10 vs. 3/5) representing the same "true" reliability.
2. Compute current `pass@k` for both via `_estimate_pass_at_k`.
3. Show the values differ despite identical underlying reliability.

**Expected result**: `pass@5` for 6/10 ≠ `pass@5` for 3/5, even though both represent a
60% per-attempt success rate — demonstrating the formula is sensitive to `tests_total`,
an arbitrary property of the test suite, not of agent behavior.

---

### Experiment 2: `reliability@k` Implementation and Comparison (H2)
**Hypothesis (H2)**: A correctly parameterized `reliability@k` — computed from `n`
independent rollouts per task (`c` = rollouts with `execution_success = True`) — produces
a leaderboard that diverges from the current `pass@k` leaderboard.

**Protocol**:
1. Extend `data.py` with a rollout generator: `n=5–10` independent
   `AgentSubmission`/`ExecutionResult` pairs per `(task, agent)`, with per-rollout pass
   rates drawn from a distribution centered on each agent's "true" skill level (simulating
   run-to-run variance).
2. Implement `reliability_at_k(results, k)` in `evaluate.py`: group `ExecutionResult`s by
   `(task_id, agent_name)`, set `n = len(rollouts)`, `c = count(execution_success)`, apply
   `pass_at_k(n, c, k)` per task, average across tasks.
3. Compute both `pass@5` (current) and `reliability@5` (new) for all agents on the same
   task set.
4. Compare rankings via Spearman correlation.

```python
# Proposed implementation sketch
def reliability_at_k(results: List[ExecutionResult], k: int) -> float:
    grouped: Dict[Tuple[str, str], List[ExecutionResult]] = {}
    for r in results:
        grouped.setdefault((r.task_id, r.agent_name), []).append(r)

    scores = []
    for rollouts in grouped.values():
        n = len(rollouts)
        c = sum(1 for r in rollouts if r.execution_success)
        scores.append(pass_at_k(n, c, k))
    return sum(scores) / len(scores) if scores else 0.0
```

**Expected results**:
- `reliability@5` will not exhibit the "everything saturates near 1.0" artifact seen in
  the baseline, since `n` is now the actual rollout count (5–10), not `tests_total`.
- Agents with high run-to-run variance (occasionally fail completely vs. consistently
  partially pass) will rank differently under `reliability@k` than under current `pass@k`.

---

### Experiment 3: Cheap-Proxy Correlation (H3)
**Hypothesis (H3)**: A single-rollout proxy score correlates with `reliability@k` well
enough to serve as a low-cost substitute when repeated rollouts are too expensive.

**Protocol**:
1. For each `(task, agent)`, take only the *first* rollout and compute
   `functional_correctness_score`, `regression_rate`, and `tool_calls_used`.
2. Correlate (Spearman/Pearson) this single-rollout proxy against the full-rollout
   `reliability@k` from Experiment 2.
3. Report correlation per agent and overall.

**Expected results**: Moderate correlation overall, but the proxy will systematically
under- or over-estimate `reliability@k` for agents with high rollout variance, since a
single run cannot observe variance at all.

---

## Expected Results Summary

| Metric | Computed From | Key Finding (Expected) |
|---|---|---|
| Current `pass@k` | `tests_total`/`tests_passed` (single submission) | Saturates near 1.0 regardless of true reliability (category error, H1) |
| `reliability@k` | `n` rollouts, `c` = fully-passing rollouts | Diverges from current `pass@k` rankings (H2) |
| Single-rollout proxy | `functional_correctness_score`, `regression_rate`, `tool_calls_used` | Partial correlation with `reliability@k`; misses variance (H3) |

**Primary claim**: CodeBench's current `pass@k` does not measure agent reliability;
`reliability@k`, computed from repeated rollouts, does — at the cost of `n`x compute. A
single-rollout proxy recovers some but not all of this signal.

---

## Why This Matters

**For benchmark designers**: a concrete, fixable methodological flaw in a widely-reused
metric (`pass@k`) when applied outside its original sampling-based context.

**For tooling teams (Anthropic, OpenAI, Anote, etc.)**: reliability/variance metrics
directly inform product decisions — e.g., whether to invest in self-consistency
mechanisms, retries, or verification passes.

**For practitioners**: teams currently choose agents based on leaderboards; if the
"reliability" column is computed with an invalid formula, they may pick agents based on a
meaningless number — or miss agents that are actually more consistent in practice.

---

## Implementation Plan

```
src/codebench/
├── core.py          # add: pass_at_k (existing) — no change needed
├── data.py          # add: make_rollout_benchmark(n_rollouts, ...) rollout generator
├── evaluate.py       # add: reliability_at_k(), single-rollout proxy helper
└── ...

tests/
├── test_evaluate.py  # add: tests for reliability_at_k, H1 counter-example regression test
└── test_data.py      # add: tests for rollout generator
```

---

## Timeline

| Phase | Duration | Deliverable |
|---|---|---|
| H1 counter-example + regression test | 1 week | Proof that current `pass@k` is a category error |
| Rollout generator in `data.py` | 1 week | `make_rollout_benchmark(n_rollouts=5..10)` |
| `reliability_at_k` implementation + tests | 1 week | New metric in `evaluate.py` |
| Comparison run (current `pass@k` vs `reliability@k`) | 1 week | Leaderboard diff, Spearman correlation |
| Cheap-proxy correlation analysis (H3) | 1 week | Correlation table, discussion |
| Write-up | 2 weeks | Draft for target venue |

---

## Open Questions & Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Synthetic rollout variance model may not reflect real agent behavior | High | Validate against real agent traces if/when access is available |
| `reliability@k` requires `n`x compute vs. current single-run setup | High | H3 cheap-proxy analysis as a mitigation |
| Choice of variance distribution (Beta vs. Normal) affects results | Medium | Sensitivity analysis across distributions |
| `execution_success` as success criterion may be too coarse | Low | Consider threshold on `pass_rate` (e.g., `>= 0.95`) as alternative |

---

## Related Issues

- Existing `functional_correctness_score` weight-normalization fix (separate branch)
- CI build-backend fixes (separate branch)
- Reproducibility: rollout generator should be seedable for deterministic experiments
