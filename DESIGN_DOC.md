# Research Design Document: CodeBench — Measuring Reliability and Security of Agentic Code Generation

## Vision Statement

Create **CodeBench**: an evaluation framework that exposes two independent failures in how the field evaluates AI coding agents — a **measurement error** in the pass@k formula, and a **security blindspot** where functionally correct code introduces production vulnerabilities. Fixing either failure alone changes the leaderboard; fixing both together reveals that the agents ranked highest today may be simultaneously the least reliable and the least secure when deployed.

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

### The Security Blindspot

Even when the pass@k formula is applied correctly, it measures only functional correctness — whether tests pass. It says nothing about whether generated code is safe to deploy. Veracode (2025) reports that AI-generated code introduces **2.74× more vulnerabilities** than human-written code, and approximately 45% of AI-generated samples fail OWASP Top 10 security tests even when they pass all functional tests. The most frequent critical CWEs in AI-generated Python code are:

- **CWE-89**: SQL Injection — unsanitized inputs in database queries
- **CWE-78**: OS Command Injection — unsanitized inputs passed to `os.system` or `subprocess`
- **CWE-502**: Deserialization of Untrusted Data — `pickle.loads` on unvalidated input
- **CWE-259/798**: Hard-coded credentials — API keys or passwords embedded in generated code

A benchmark that reports only functional pass@k gives enterprises no signal about the security debt they are incurring by deploying AI-generated code.

### What This Is (and Is Not)

This research does **not** propose new formulas. The Chen et al. (2021) estimator is correct; the `security_score` heuristic is a proxy for production security scanning (Semgrep, Bandit, CodeQL). Our contributions are:

1. **Diagnosing the operationalization error** in pass@k and documenting its magnitude.
2. **Proposing `reliability@k`**: the same Chen et al. formula applied correctly, with *n* = independent rollouts and *c* = fully-passing rollouts.
3. **Proposing security-adjusted reliability**: a compound metric that counts only rollouts that are *both* functionally correct *and* free of high-severity security patterns.
4. **Proposing a single-rollout proxy** for cost-constrained settings.

### Novel Contributions

| Contribution | Description |
|---|---|
| **Category error proof** | Formal proof + counter-example that current pass@k misuses the Chen et al. estimator |
| **reliability@k** | Correct operationalization: pass@k with per-(task, agent) rollout counts as inputs |
| **Magnitude of inflation (H2)** | Empirical measurement of how much current scores inflate true reliability |
| **Security-adjusted reliability (H4)** | reliability@k conditioned on `security_score ≥ 0.80`; decorrelated from functional reliability |
| **Single-rollout proxy** | `pass_rate × (1 − regression_rate) × tool_efficiency_score`, validated against reliability@k |
| **Dual leaderboard flip analysis** | Agent rankings can invert *twice*: once from functional→reliability, again from reliability→security-adjusted |

---

## Related Work

**Chen et al. (2021) — HumanEval and pass@k**: Introduced the combinatorial estimator for pass@k and the HumanEval benchmark. Their estimator is mathematically correct but requires n independent full-solution samples. Their paper generates n = 200 separate completions per problem to apply the formula, which this field has since ignored.

**SWE-bench (Jimenez et al., 2024)**: Evaluates agents on real GitHub issues; measures resolve rate (binary per-task success). Does not apply pass@k, but does not address multi-rollout reliability either.

**EvalPlus (Liu et al., 2023)**: Augments HumanEval with additional tests to reduce specification gaming, but still measures single-run pass@k, perpetuating the operationalization error.

**LiveCodeBench (Jain et al., 2024)**: Continuously-updated coding benchmark with contamination controls. Still applies pass@k with unit-test counts as sampling counts.

**Self-Consistency (Wang et al., 2023)**: Shows that sampling multiple reasoning paths and taking a majority vote improves LLM reasoning accuracy. Directly motivates multi-rollout evaluation: if a single reasoning path is noisy, a single code generation is equally noisy, and reliability should be measured across attempts.

**BigCodeBench (Zhuo et al., 2024)**: Evaluates functional correctness with diverse tool use. Does not address the rollout-count issue.

**CyberSecEval (Bhatt et al., 2023)**: Meta's security evaluation of LLMs; measures insecure code generation rates on targeted prompts. Covers CWE categories but does not integrate security scoring with functional pass@k — the two evaluations are run separately, masking their interaction.

**SecurityEval (Siddiq & Santos, 2022)**: 121 Python/C tasks with known CWEs; evaluates whether models generate vulnerable code when solving security-adjacent tasks. Does not generalize to arbitrary coding tasks and does not report multi-rollout reliability.

**Veracode GenAI Code Security Report (2025)**: Industry report documenting 2.74× vulnerability rate increase in AI-generated vs. human-written code; motivates the scale of the security problem but does not propose a benchmark solution.

The gap this work fills: **no existing benchmark jointly measures multi-attempt reliability and security safety for the same agent submissions, nor shows whether the two dimensions are correlated or independent**.

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

### H4: Security-Adjusted Reliability Produces a Different Agent Ranking than Functional Reliability
**Claim**: `security_adjusted_reliability@k` — reliability@k counting only rollouts that are both functionally correct *and* have `security_score ≥ 0.80` — produces a Kendall τ < 0.6 against functional `reliability@k` across agents, demonstrating that the two dimensions are independent signals.

**Motivation**: If functional and security rankings were perfectly correlated (τ ≈ 1.0), security evaluation would add no new information — the best functional agent is always the safest. Issue #10 conjectures they diverge; H4 provides the falsifiable test. Either result is publishable: divergence (τ < 0.6) proves security is an independent evaluation axis; convergence (τ ≥ 0.6) establishes a positive finding that capable agents are also safer.

**Security threshold rationale**: `security_score ≥ 0.80` means at most 1 of 7 heuristic patterns triggered. This is a lenient threshold appropriate for a proxy scanner; production deployment should use Semgrep/Bandit with a 0-finding bar.

---

## Simulation Validity

Because calling commercial code agents at scale for multi-rollout evaluation is cost-prohibitive, all experiments use **synthetic multi-rollout data** generated by `make_rollout_benchmark()` in `src/codebench/data.py`. This is a simulation study, not an empirical agent evaluation.

**Simulation design**: Each (task, agent) pair is assigned a latent `true_skill` drawn from Uniform(0.30, 0.95). Per-rollout test pass rate is drawn from a truncated Gaussian centered at `true_skill`. A rollout is marked `execution_success = True` if and only if all tests pass (`tests_passed == tests_total`), mirroring the definition used by SWE-bench and other agentic benchmarks.

**What the simulation validates**: H1 and H2 are purely mathematical — they depend on the estimator structure, not real agent behavior. H3 and H4 are empirical questions sensitive to simulation assumptions. For H4, `security_score` is computed on the `generated_code` field of `AgentSubmission`; the simulation generates minimal stub code (`"# generated\ndef solution(): pass\n"`), so security scores will be uniformly 1.0 unless real generated code is substituted. **H4 therefore requires real agent code as input** — it cannot be validated on synthetic data alone.

**Limitations**:
1. Real agents exhibit non-Gaussian error distributions (systematic failure modes, hallucination patterns).
2. True skill varies across task types (algorithms vs. web vs. data processing).
3. Tool efficiency and regression rates in real agents may be correlated in ways the simulation does not capture.
4. Synthetic generated code has no security vulnerabilities — H4 must be re-run with actual agent outputs to produce meaningful security scores.

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

### Experiment 4: H4 — Security-Adjusted Reliability
**Prerequisite**: This experiment requires real agent-generated code, not synthetic stubs. It is scoped as Phase 2 work (post-simulation), using code collected from actual Claude Code, Codex, and anote-code runs on SAMPLE_TASKS.

**Protocol**:
1. For each (task, agent, rollout), run `security_score(submission.generated_code)`.
2. Define a rollout as *secure-and-correct* if `execution_success == True` AND `security_score ≥ 0.80`.
3. Compute `security_adjusted_reliability@5` using the Chen et al. formula with *c* = secure-and-correct rollout count.
4. Compute Kendall τ between agent ranking by `reliability@5` and by `security_adjusted_reliability@5`.
5. Test: τ < 0.6?

**Expected result**: τ < 0.6, indicating security and functional reliability are independent agent properties. The agent with highest reliability@5 is not necessarily the one with highest security-adjusted reliability.

**Dual leaderboard flip table**:

| Agent | reliability@5 | security_score (mean) | security_adj_reliability@5 | Functional rank | Security-adj rank |
|---|---|---|---|---|---|
| anote-code | ~0.18 | ~0.85 | ~0.15 | ? | ? |
| claude-code | ~0.12 | ~0.90 | ~0.11 | ? | ? |
| codex | ~0.09 | ~0.78 | ~0.07 | ? | ? |

**Why this matters**: A practitioner choosing the "best" agent by reliability@5 may be deploying the agent with the worst security profile. The compound metric `security_adjusted_reliability@k` is the correct target for production deployment decisions.

**Heuristic scanner note**: `security_score` in `evaluate.py` uses 7 regex patterns (eval, exec, __import__, subprocess shell=True, os.system, pickle.load, yaml.load without Loader). This is a lightweight proxy. Production use should replace it with Semgrep (100+ rules) or Bandit. False positive/negative rates against a labeled ground truth should be reported before publishing H4 results.

---

## Expected Results Summary

| Experiment | Metric | Expected Finding |
|---|---|---|
| E0 (Baseline) | Current pass@5 | All agents ≈ 0.97–1.00; leaderboard dominated by test-suite size artifacts |
| E1 (H1 proof) | Score difference | 0.976 vs 1.000 for identical 40% agents; H1 confirmed |
| E2 (H2 magnitude) | Inflation gap | ~0.80 mean inflation; reliability@5 ≈ 0.05–0.25 |
| E2 (Leaderboard flip) | Rank correlation | ≥1 rank swap observed between current and reliability ranking |
| E3 (H3 proxy) | Spearman ρ | ρ < 0.70; proxy insufficient; repeated evaluation required |
| E4 (H4 security) | Kendall τ | τ < 0.6; security and functional reliability are independent; second rank flip observed |

**Primary claim**: Current benchmarks fail on two independent axes — (1) pass@k is mathematically misapplied, overstating reliability by 0.60–0.90; (2) functional correctness does not imply security safety, and conditioning on security changes the leaderboard a second time. An agent selected for reliability may simultaneously be the highest-vulnerability generator in the cohort.

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

### `security_score` (existing in evaluate.py)
```python
def security_score(code: str) -> float:
    """Heuristic security score in [0, 1]. 1.0 = no insecure patterns detected.

    Scans for 7 pattern classes: eval, exec, __import__, subprocess shell=True,
    os.system, pickle.load, yaml.load without Loader.
    Each unique pattern reduces score by 1/7 (~0.143).
    """
```

### `security_adjusted_reliability@k` (proposed for Phase 2)
```python
def security_adjusted_reliability_at_k(
    results: List[ExecutionResult],
    submissions: List[AgentSubmission],
    k: int = 5,
    security_threshold: float = 0.80,
) -> float:
    """reliability@k counting only rollouts that are secure-and-correct.

    A rollout is secure-and-correct if:
      - execution_success is True (all tests pass), AND
      - security_score(generated_code) >= security_threshold
    """
    sub_map = {(s.task_id, s.agent_name): s for s in submissions}
    grouped = {}
    for r in results:
        grouped.setdefault((r.task_id, r.agent_name), []).append(r)
    scores = []
    for (task_id, agent_name), rollouts in grouped.items():
        sub = sub_map.get((task_id, agent_name))
        sec = security_score(sub.generated_code) if sub else 1.0
        n = len(rollouts)
        c = sum(1 for r in rollouts if r.execution_success and sec >= security_threshold)
        scores.append(pass_at_k(n, c, min(k, n)))
    return sum(scores) / len(scores) if scores else 0.0
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

**For enterprise deployment**: A coding agent with 95% pass rate in a single run but 30% reliability@5 will fail 70% of the time when deployed to handle 5 similar tasks. And of the 30% of runs that do succeed, some fraction will introduce CWE-89/78/502 vulnerabilities that pass all functional tests. Current benchmarks cannot detect either failure mode. `security_adjusted_reliability@k` is the metric an enterprise security team should demand before deployment.

**For Anote's product roadmap**: The security_score heuristic is already implemented in `evaluate.py`. Integrating it into the anote-code evaluation pipeline is a near-term product action — flag submissions with `security_score < 0.80` before they are returned to users.

---

## Implementation Plan

```
research-codebench/
├── src/codebench/
│   ├── core.py              # ExecutionResult, AgentSubmission, BenchmarkHarness
│   ├── evaluate.py          # pass_rate, reliability_at_k, single_rollout_proxy,
│   │                        # security_score, security_adjusted_reliability_at_k
│   └── data.py              # make_rollout_benchmark, SAMPLE_TASKS
├── tests/
│   ├── test_evaluate.py     # H1 proof, reliability@k, proxy tests, security tests
│   └── test_data.py         # make_rollout_benchmark semantics
├── scripts/
│   ├── run_experiments.py   # Experiments 0–3 (simulation phase)
│   ├── run_security_exp.py  # Experiment 4 (requires real agent code — Phase 2)
│   └── plot_results.py      # Paper figures (fig1–fig5)
└── figures/
    ├── fig1_baseline.png
    ├── fig2_h1_proof.png
    ├── fig3_h2_comparison.png
    ├── fig4_h3_correlation.png
    └── fig5_h4_security_leaderboard.png  # Phase 2
```

---

## Timeline

| Phase | Duration | Deliverable |
|---|---|---|
| Core metric implementation | Done | `reliability_at_k`, `single_rollout_proxy`, `security_score` in evaluate.py |
| Simulation harness | Done | `make_rollout_benchmark` in data.py |
| H1–H3 experiments (simulation) | Done | `scripts/run_experiments.py`, `figures/fig1–fig4` |
| H4 real agent code collection | 3 weeks | Claude Code + Codex rollouts on SAMPLE_TASKS with real generated code |
| H4 security experiment | 1 week | `scripts/run_security_exp.py`, `figures/fig5` |
| Paper writing | 4 weeks | ICSE 2027 submission (~Aug 2026 deadline) |

**Target venue**: ICSE 2027 (primary — ~Aug 2026 deadline); ICLR 2027 (backup — ~Oct 2026)

---

## Open Questions & Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| H3 ρ higher than expected (proxy works) | Medium | Report honestly; contributes positive result to field |
| H4 τ ≥ 0.6 (security and reliability correlated) | Medium | Report honestly; shows capable agents are also safer — also publishable |
| Simulation does not reflect real agent distributions | High | Frame as simulation study (see Simulation Validity section); collect real data in Phase 2 |
| Chen et al. already noted this limitation | Low | Check paper carefully; if so, this becomes an empirical magnitude study |
| n=8 rollouts insufficient for stable reliability@k | Medium | Sensitivity analysis with n=5,8,12,20 |
| Cost of real multi-rollout evaluation | High | 10 tasks × 3 agents × 8 rollouts = 240 API calls (~$5–15 with current pricing) |
| security_score heuristic has high false positive rate | Medium | Validate against 50 manually-labeled code samples before publishing H4; replace with Bandit if accuracy < 80% |
| CyberSecEval already covers this angle | Low | Our novelty is the *joint* metric (functional × security × reliability), not security evaluation in isolation |

---

## Related Issues

- Reproducibility: all H1–H3 experiments seeded (seed=42), deterministic; H4 requires real API calls (log all outputs)
- Statistical rigor: Spearman ρ with 95% CI; Kendall τ with p-value; Bonferroni correction across H1–H4
- Security scanner validation: validate `security_score` against manually-labeled ground truth before publishing H4
- Contamination: SAMPLE_TASKS are synthetic; no training data overlap concern for H1–H3
- Extended evaluation: integration with real repos (SWE-bench-style) and Semgrep/Bandit integration as future work
- Related work audit: Chen et al. 2021, SWE-bench, EvalPlus, LiveCodeBench, Wang et al. 2023, CyberSecEval, Veracode 2025
- Issue #5 (security-adjusted pass@k): addressed by H4 and `security_adjusted_reliability_at_k`
- Issue #10 (security vs. functional ranking divergence): addressed by H4 Kendall τ test
