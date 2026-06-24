# Research Design Document: CodeBench — Measuring Reliability of Agentic Code Generation

## Vision Statement

Create **CodeBench**: an evaluation framework that measures AI coding agents on *verified correctness, reliability across repeated attempts, security safety, and specification fidelity* — moving beyond the misapplied pass@k metric to capture the dimensions that matter in production software engineering. The central contribution is identifying and correcting a fundamental measurement error in how the field evaluates multi-attempt code generation, then providing a practical single-rollout proxy that avoids the cost of repeated evaluation.

---

## Problem Statement & Novelty

### The Core Measurement Error

Existing coding benchmarks (HumanEval, MBPP, SWE-bench, LiveCodeBench) apply the pass@k estimator from Chen et al. (2021) using within-submission test counts as sampling counts. This violates the fundamental assumption of the estimator.

**Formal statement of the i.i.d. assumption**: The Chen et al. (2021) unbiased estimator

$$\widehat{\text{pass@}k} = 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}$$

is valid only when *n* is the number of **independent, identically distributed full-solution samples** and *c* is the number of those samples that are fully correct. The estimator assumes each of the *n* items is a fresh generation from the same distribution.

**The category error**: Current practice substitutes *n* = `tests_total` (the number of unit tests in a single run) and *c* = `tests_passed`. These are not independent rollouts — they are sub-results of a single execution. This violates the i.i.d. requirement in two ways:
1. Unit tests within one submission are correlated (a bug affects many tests simultaneously).
2. There is exactly one generation sample, not *n* independent ones.

**Consequence — proof by counterexample**: Two agents with identical 40% task reliability receive different pass@k scores because they happen to have different test-suite sizes:

| Agent | Submission | tests_passed/tests_total | True reliability | Current pass@5 |
|---|---|---|---|---|
| Agent-A | 1 rollout, 10 tests | 4/10 = 0.40 | 40% | 0.976 |
| Agent-B | 1 rollout, 5 tests | 2/5 = 0.40 | 40% | 1.000 |

Agent-B appears better by current scoring despite being statistically identical. The test-suite size determines the score, not the agent's reliability.

### What This Is (and Is Not)

This research does **not** propose a new formula. The Chen et al. (2021) estimator is correct — it is simply being applied to the wrong inputs. Our contribution is:

1. **Diagnosing the operationalization error** and documenting its magnitude on a benchmark harness.
2. **Proposing `reliability@k`**: the same formula applied correctly, with *n* = number of independent rollouts per (task, agent) and *c* = number of rollouts achieving execution success (all tests passing).
3. **Proposing a single-rollout proxy** for settings where repeated rollouts are cost-prohibitive.

### Novel Contributions

| Contribution | Description |
|---|---|
| **Category error proof** | Formal proof + counter-example that current pass@k misuses the Chen et al. estimator |
| **reliability@k** | Correct operationalization: pass@k with per-(task, agent) rollout counts as inputs |
| **Magnitude of inflation (H2)** | Empirical measurement of how much current scores inflate true reliability |
| **Single-rollout proxy** | `pass_rate × (1 − regression_rate) × tool_efficiency_score`, validated against reliability@k |
| **Leaderboard flip analysis** | Demonstration that agent rankings can invert when using the correct metric |

---

## Related Work

**Chen et al. (2021) — HumanEval and pass@k**: Introduced the combinatorial estimator for pass@k and the HumanEval benchmark. Their estimator is mathematically correct but requires n independent full-solution samples. Their paper generates n = 200 separate completions per problem to apply the formula, which this field has since ignored.

**SWE-bench (Jimenez et al., 2024)**: Evaluates agents on real GitHub issues; measures resolve rate (binary per-task success). Does not apply pass@k, but does not address multi-rollout reliability either.

**EvalPlus (Liu et al., 2023)**: Augments HumanEval with additional tests to reduce specification gaming, but still measures single-run pass@k, perpetuating the operationalization error.

**LiveCodeBench (Jain et al., 2024)**: Continuously-updated coding benchmark with contamination controls. Still applies pass@k with unit-test counts as sampling counts.

**Self-Consistency (Wang et al., 2023)**: Shows that sampling multiple reasoning paths and taking a majority vote improves LLM reasoning accuracy. Directly motivates multi-rollout evaluation: if a single reasoning path is noisy, a single code generation is equally noisy, and reliability should be measured across attempts.

**BigCodeBench (Zhuo et al., 2024)**: Evaluates functional correctness with diverse tool use. Does not address the rollout-count issue.

The gap this work fills: **no existing benchmark correctly operationalizes multi-attempt reliability for agentic code generation using the Chen et al. estimator**.

---

## Research Hypotheses

### H1: The i.i.d. Violation Produces Measurable Score Differences
**Claim**: Two agents with identical per-rollout success rates receive different current pass@k scores based solely on test-suite size.

**Falsifiable condition**: Demonstrate at least one pair (Agent-A, Agent-B) where `pass_rate(A) == pass_rate(B)` but `_estimate_pass_at_k(A) ≠ _estimate_pass_at_k(B)`.

### H2: Current pass@k Inflates True Reliability
**Claim**: Current `_estimate_pass_at_k` scores are on average >0.5 higher than `reliability@k` computed from the same agents' rollout data.

**Falsifiable condition**: On a rollout benchmark with agents having true success rates in [0.30, 0.95], the mean inflation (current − reliability) > 0.50.

### H3: Single-Rollout Proxy is Insufficient as a Reliability Substitute
**Claim**: The proxy `pass_rate × (1 − regression_rate) × tool_efficiency_score` does not correlate sufficiently with `reliability@k` to substitute for it (Spearman ρ < 0.70).

**Threshold rationale**: ρ ≥ 0.70 is a standard "strong correlation" threshold in psychometrics and is commonly used to validate surrogate metrics in software engineering research (Kitchenham & Pfleeger, 2008). A proxy below this threshold cannot reliably rank agents and should not replace repeated evaluation.

**Fallback strategy**: If ρ < 0.70, the recommended approach is to collect n ≥ 5 rollouts per (task, agent) pair and apply reliability@k directly. If budget allows only a single rollout, report pass_rate without pass@k framing to avoid implying multi-attempt guarantees.

---

## Simulation Validity

Because calling commercial code agents at scale for multi-rollout evaluation is cost-prohibitive, all experiments use **synthetic multi-rollout data** generated by `make_rollout_benchmark()` in `src/codebench/data.py`. This is a simulation study, not an empirical agent evaluation.

**Simulation design**: Each (task, agent) pair is assigned a latent `true_skill` drawn from Uniform(0.30, 0.95). Per-rollout test pass rate is drawn from a truncated Gaussian centered at `true_skill`. A rollout is marked `execution_success = True` if and only if all tests pass (`tests_passed == tests_total`), mirroring the definition used by SWE-bench and other agentic benchmarks.

**What the simulation validates**: The simulation makes H1 and H2 purely mathematical — they depend on the structure of the estimator, not on real agent behavior. The simulation confirms what the math already proves. H3 is the only empirical question and the one most sensitive to simulation assumptions.

**Limitations**:
1. Real agents exhibit non-Gaussian error distributions (systematic failure modes, hallucination patterns).
2. True skill varies across task types (algorithms vs. web vs. data processing).
3. Tool efficiency and regression rates in real agents may be correlated in ways the simulation does not capture.

**Simulation is sufficient for**: Demonstrating the magnitude of H1 and H2 effects. Establishing a lower bound on inflation. Motivating the need for real multi-rollout data collection.

**Future work**: Replace synthetic rollouts with real multi-agent rollout data collected from Claude Code, GitHub Copilot, and Codex on the SAMPLE_TASKS benchmark.

---

## Systems Under Evaluation (Synthetic)

| Agent | Simulated true skill | Description |
|---|---|---|
| anote-code | Uniform(0.30, 0.95) | Anote's internal coding agent |
| claude-code | Uniform(0.30, 0.95) | Anthropic Claude Code |
| codex | Uniform(0.30, 0.95) | OpenAI Codex / GPT-4o |

All agents draw from the same distribution in the simulation. Differences in experiment results are due to random seed variation, not systematic agent differences. This is appropriate for validating the metric (H1–H3) rather than ranking real agents.

---

## Dataset

**Benchmark tasks**: `SAMPLE_TASKS` in `src/codebench/data.py` — 10 Python implementation tasks spanning algorithm, data structure, system integration, and API design categories. Tasks are drawn from realistic repository names (anote-ai/repo-parser, anote-ai/data-pipeline, etc.) and include reference solutions.

**Rollout data**: Generated by `make_rollout_benchmark(n_tasks=10, agents=3, n_rollouts=8, seed=42)`, producing 240 synthetic execution results (10 tasks × 3 agents × 8 rollouts). Each result records `tests_passed`, `tests_total`, `regression_count`, and `execution_success`.

**No external datasets are required for H1–H3** as the hypotheses concern metric behavior, not agent behavior.

---

## Experimental Design

### Experiment 0: Baseline — Current Leaderboard (Experiment 0)
**Protocol**: Run `make_benchmark(n_tasks=10)` with 3 agents. Compute pass@1, pass@5 (current estimator), mean_pass_rate, mean_latency_ms, mean_cost_usd. Display leaderboard.

**Purpose**: Establish the current state of scoring that subsequent experiments critique.

**Expected result**: All agents score pass@5 ≈ 0.97–1.0 despite having mean pass rates of 0.60–0.75. This high inflation already hints at H2.

---

### Experiment 1: H1 — Proof of i.i.d. Violation
**Protocol**:
1. Construct Agent-A with `tests_passed=4, tests_total=10` (40% pass rate).
2. Construct Agent-B with `tests_passed=2, tests_total=5` (40% pass rate).
3. Compute `_estimate_pass_at_k` for both with k=5.
4. Assert `pass_rate(A) == pass_rate(B)` and `pass@5(A) ≠ pass@5(B)`.

**Expected result**:
- Agent-A: pass@5 = 1 − C(6,5)/C(10,5) ≈ **0.976**
- Agent-B: pass@5 = 1.000 (n−c = 3 < k=5, formula returns 1.0)
- Same underlying reliability; different scores due to test-suite size alone.

---

### Experiment 2: H2 — Magnitude of Score Inflation
**Protocol**:
1. Generate rollout benchmark (10 tasks, 3 agents, 8 rollouts).
2. Compute `reliability@k` (k=5): apply Chen et al. formula with n=8 rollouts, c=successful rollouts per (task, agent).
3. Compute current `_estimate_pass_at_k` (k=5) on single-rollout aggregated results.
4. Report mean, max, and distribution of (current − reliability@k).

**Expected result**: Mean inflation ≈ 0.85–0.97 (current) vs 0.05–0.25 (reliability@k). The current estimator's near-1.0 scores are artifacts of small test-suite sizes satisfying n−c < k, not evidence of high agent reliability.

#### Leaderboard Flip Analysis
Apply both metrics to rank the 3 agents. Check whether the ordinal ranking of agents is preserved when switching from current pass@k to reliability@k.

| Agent | Current pass@5 | reliability@5 | Current rank | Reliability rank |
|---|---|---|---|---|
| anote-code | ~0.975 | ~0.12 | ? | ? |
| claude-code | ~0.981 | ~0.18 | ? | ? |
| codex | ~0.970 | ~0.09 | ? | ? |

**Hypothesis for flip**: Because current pass@k is nearly saturated for all agents, small differences in `tests_total` can flip rank order. reliability@k, based on full-task success counts, amplifies real differences. If a rank flip is observed, it documents that the current metric not only inflates scores but **misorients development priorities**.

---

### Experiment 3: H3 — Proxy Validity
**Protocol**:
1. For each (task, agent) pair in the rollout benchmark, compute:
   - `reliability@5` (ground truth)
   - `proxy = pass_rate × (1 − regression_rate) × tool_efficiency_score`
2. Compute Spearman ρ and p-value between proxy scores and reliability@5 scores.
3. Test: ρ ≥ 0.70?

**Expected result**: ρ ≈ 0.30–0.45 (below threshold), p > 0.05. The proxy captures per-submission quality signals (test coverage, regression count, tool use) but does not capture whether the agent can consistently pass **all** tests across independent attempts, which is what reliability@k measures.

**Interpretation if ρ < 0.70**: The single-rollout proxy cannot substitute for repeated evaluation. Reporting proxy as a reliability estimate overstates agent consistency. Practitioners should collect at minimum n = 5 rollouts before making deployment decisions.

---

## Expected Results Summary

| Experiment | Metric | Expected Finding |
|---|---|---|
| E0 (Baseline) | Current pass@5 | All agents ≈ 0.97–1.00; leaderboard dominated by test-suite size artifacts |
| E1 (H1 proof) | Score difference | 0.976 vs 1.000 for identical 40% agents; H1 confirmed |
| E2 (H2 magnitude) | Inflation gap | ~0.80 mean inflation; reliability@5 ≈ 0.05–0.25 |
| E2 (Leaderboard flip) | Rank correlation | ≥1 rank swap observed between current and reliability ranking |
| E3 (H3 proxy) | Spearman ρ | ρ < 0.70; proxy insufficient; repeated evaluation required |

**Primary claim**: Current benchmarks applying pass@k to within-submission test counts overstate agent reliability by 0.60–0.90 in absolute score terms and can invert agent rankings; the correct operationalization (reliability@k) requires independent rollout data that single-run benchmarks do not collect.

---

## Metrics Reference

### `reliability@k`
```python
def reliability_at_k(results: List[ExecutionResult], k: int = 5) -> float:
    """Correct operationalization of Chen et al. (2021) pass@k.

    n = independent rollouts per (task, agent)
    c = rollouts where execution_success is True (all tests pass)
    """
    grouped = {}
    for r in results:
        grouped.setdefault((r.task_id, r.agent_name), []).append(r)
    scores = []
    for rollouts in grouped.values():
        n = len(rollouts)
        c = sum(1 for r in rollouts if r.execution_success)
        scores.append(pass_at_k(n, c, min(k, n)))
    return sum(scores) / len(scores) if scores else 0.0
```

### `single_rollout_proxy`
```python
def single_rollout_proxy(result: ExecutionResult, submission: AgentSubmission) -> float:
    """Cheap proxy for reliability from a single rollout.

    proxy = pass_rate × (1 − regression_rate) × tool_efficiency_score
    Valid as reliability substitute only if Spearman ρ ≥ 0.70 (H3).
    """
    pr = result.pass_rate                          # tests_passed / tests_total
    reg = result.regression_count / max(result.tests_total, 1)
    eff = max(0.0, 1.0 - submission.tool_calls_used / 20)
    return pr * (1.0 - reg) * eff
```

### `_estimate_pass_at_k` (current — documented as incorrect)
```python
# n = tests_total (NOT independent rollouts) — violates i.i.d. assumption
# c = tests_passed (NOT successful full-solution samples) — violates i.i.d. assumption
scores.append(pass_at_k(max(r.tests_total, k), r.tests_passed, k))
```

---

## Why This Matters

**For researchers**: Every paper reporting "pass@k improved by X%" on a single-run benchmark is reporting a number that depends on test-suite size, not agent capability. H2 shows the effect can be 4–10× in absolute terms.

**For practitioners at Anote**: When evaluating whether anote-code has improved across versions, reliability@k computed over ≥5 rollouts per task is the correct comparison. Single-run pass rates can be identical even when one version is substantially more reliable.

**For the field**: Wang et al. (2023) showed that self-consistency over multiple reasoning paths improves LLM accuracy; the same logic applies to code generation. The field should move toward multi-rollout evaluation as the standard protocol, not a special case.

**For enterprise deployment**: A coding agent with 95% pass rate in a single run but 30% reliability@5 will fail 70% of the time when deployed to handle 5 similar tasks. Current benchmarks cannot distinguish this from a genuinely reliable agent.

---

## Implementation Plan

```
research-codebench/
├── src/codebench/
│   ├── core.py              # ExecutionResult, AgentSubmission, BenchmarkHarness
│   ├── evaluate.py          # pass_rate, reliability_at_k, single_rollout_proxy
│   └── data.py              # make_rollout_benchmark, SAMPLE_TASKS
├── tests/
│   ├── test_evaluate.py     # H1 proof, reliability@k, proxy tests
│   └── test_data.py         # make_rollout_benchmark semantics
├── scripts/
│   ├── run_experiments.py   # Experiments 0–3
│   └── plot_results.py      # Paper figures (fig1–fig4)
└── figures/
    ├── fig1_baseline.png
    ├── fig2_h1_proof.png
    ├── fig3_h2_comparison.png
    └── fig4_h3_correlation.png
```

---

## Timeline

| Phase | Duration | Deliverable |
|---|---|---|
| Core metric implementation | Done | `reliability_at_k`, `single_rollout_proxy` in evaluate.py |
| Simulation harness | Done | `make_rollout_benchmark` in data.py |
| H1–H3 experiments | Done | `scripts/run_experiments.py` |
| Paper figures | Done | `scripts/plot_results.py`, `figures/` |
| Real agent data collection | 4 weeks | Actual Claude Code / Codex rollouts on SAMPLE_TASKS |
| Paper writing | 4 weeks | AAMAS 2027 or ICSE 2027 submission |

**Target venue**: AAMAS 2027, ICSE 2027, or NeurIPS 2026 Datasets & Benchmarks track

---

## Open Questions & Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| H3 ρ higher than expected (proxy works) | Medium | Report honestly; contributes positive result to field |
| Simulation does not reflect real agent distributions | High | Frame as simulation study (see Simulation Validity section); collect real data in Phase 2 |
| Chen et al. already noted this limitation | Low | Check paper carefully; if so, this becomes an empirical magnitude study |
| n=8 rollouts insufficient for stable reliability@k | Medium | Sensitivity analysis with n=5,8,12,20 |
| Cost of real multi-rollout evaluation | High | Focus on 10 tasks × 3 agents × 8 rollouts = 240 API calls (~$5–15 with current pricing) |

---

## Related Issues

- Reproducibility: all experiments seeded (seed=42), deterministic
- Statistical rigor: report Spearman ρ with 95% CI and p-value; Bonferroni-correct multiple comparisons
- Contamination: SAMPLE_TASKS are synthetic; no training data overlap concern
- Extended evaluation: integration with real repos (SWE-bench-style) as future work
- Related work audit: Chen et al. 2021, SWE-bench, EvalPlus, LiveCodeBench, Wang et al. 2023
