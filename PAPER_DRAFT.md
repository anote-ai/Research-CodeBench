# CodeBench: A Multi-Dimensional Benchmark for AI Coding Assistants (DRAFT SKELETON)

> **Status: skeleton / outline only.** This document mirrors the structure of
> DESIGN_DOC.md so that, as real experiments are run, sections can be filled
> in with measured numbers rather than rewritten from scratch. Anywhere a
> number appears below, it is explicitly tagged as either:
> - **(projected, pending full experiment run)** — carried over from
>   DESIGN_DOC.md's "Expected results" tables, i.e. a hypothesis, not a
>   measurement, or
> - **(measured)** — actually computed by running code in this repository,
>   with a pointer to the script/commit that produced it.
>
> As of this draft, **no entries are tagged (measured) using a real external
> model.** The only genuinely executed numbers in the repository come from
> `experiments/exp0_baseline.py`, which runs the 10 hand-written reference
> solutions in `src/codebench/data.py` through the real harness; see
> `results/exp0_baseline.json` for that output. Everything else below is
> (projected, pending full experiment run) and copied from DESIGN_DOC.md's
> hypotheses.

## Abstract (draft)

Existing code-generation benchmarks (HumanEval, MBPP, SWE-bench,
LiveCodeBench) score functional correctness in isolation, which can overstate
real-world readiness of AI coding assistants: a solution can pass all unit
tests while introducing security vulnerabilities, gaming a weak test suite,
or failing to integrate into an existing codebase. We propose CodeBench, a
benchmark and metric suite — Security Safety Rate (SSR), Specification
Gaming Rate (SGR), and Codebase Integration Rate (CIR) — designed to surface
these gaps. *(This abstract describes the planned contribution; the
empirical results needed to support its claims have not yet been collected.
See "Status" note above.)*

## 1. Introduction

See DESIGN_DOC.md "Problem Statement & Novelty" for the full motivating
argument. Summary: pass@k metrics on HumanEval/MBPP-style benchmarks have
plateaued and are increasingly contamination-prone, while saying nothing
about security or specification-gaming risk — both of which matter directly
for enterprise adoption decisions.

## 2. Related Work

*(To be filled in: HumanEval, MBPP, SWE-bench, LiveCodeBench, existing code
security benchmarks (e.g., CyberSecEval, SecurityEval), and existing
specification-gaming / reward-hacking literature. This section is currently
a placeholder — DESIGN_DOC.md lists a "related work audit" as an open
issue, not yet completed.)*

## 3. CodeBench Dataset (planned)

DESIGN_DOC.md specifies 1,800 tasks across 6 categories (algorithm
implementation, web backend, data processing/ETL, refactoring, bug fixing,
system integration), each with a functional test suite, a semantic oracle,
and human-assigned CWE/security risk labels.

**Current state (measured):** 10 example tasks exist in
`src/codebench/data.py::SAMPLE_TASKS`, each with a real reference solution
and description, but without dedicated security labels, gaming-vector
annotations, or semantic oracles. This is roughly 0.5% of the target dataset
size and should be read as a structural prototype, not a sample of the final
dataset.

## 4. Metrics

Implemented (measured, see `src/codebench/evaluate.py` and its tests in
`tests/test_evaluate.py`, `tests/test_suite_and_scoring.py`):
- `pass_rate`, `pass_at_k` (unbiased estimator)
- `regression_rate`
- `tool_efficiency_score`, `cost_adjusted_score`
- `security_score` — a **regex heuristic** over 7 known-insecure Python
  patterns (`eval`, `exec`, `__import__`, `subprocess(..., shell=True)`,
  `os.system`, `pickle.load`, unsafe `yaml.load`). This is a much cruder
  proxy than the Semgrep/Bandit/CodeQL pipeline described in DESIGN_DOC.md's
  SSR definition, and should not be reported as SSR without that caveat.
- `functional_correctness_score`, `complexity_adjusted_score`

Not yet implemented:
- SSR as specified (multi-scanner static analysis with severity
  thresholds) — only the regex proxy above exists.
- SGR (semantic oracle comparison) — no oracle implementation exists.
- CIR (real-repo-context integration) — no repo-embedding harness exists.

## 5. Experimental Results

### Experiment 0: Baseline Replication
**(measured, partial)** `experiments/exp0_baseline.py` executes the 10
reference solutions in `SAMPLE_TASKS` and computes real pass@1 values for
them via actual Python execution (not RNG). Because these are reference
solutions (not model-generated code), the expected and actual result is a
pass rate at or near 1.0 — this validates that the harness's execution and
scoring pipeline works end-to-end, but it is **not** a measurement of any
LLM's coding ability. Output: `results/exp0_baseline.json`.

**(projected, pending full experiment run)** GPT-4o ≈ 90% pass@1 on
HumanEval, per DESIGN_DOC.md Experiment 0 hypothesis. Not yet run in this
repository against any real model.

### Experiment 1: Security Safety Rate
**(projected, pending full experiment run)** All numbers in DESIGN_DOC.md's
Experiment 1 table (e.g., "Claude Sonnet 4 SSR ≈ 0.71") are hypothesized
expected results written before any model was run against the security task
set, because that task set and the Semgrep/Bandit/CodeQL pipeline do not yet
exist in this repository.

### Experiment 2: Specification Gaming Rate
**(projected, pending full experiment run)** Same status as Experiment 1:
no gameable-task set or semantic oracle exists yet to measure SGR.

### Experiment 3: Codebase Integration Rate
**(projected, pending full experiment run)** No repo-embedded task set or
CIR evaluator exists yet.

### Experiment 4: Accuracy–Security Tradeoff
**(projected, pending full experiment run)** Depends on Experiments 0 and 1
being run on real models first.

### Experiment 5: Contamination Analysis
**(projected, pending full experiment run)** Depends on a private held-out
task set that does not yet exist.

## 6. Discussion (draft)

The central claim of this work — that pass@1 systematically overstates
production-readiness by 30-40% once security and specification-gaming are
accounted for — is a hypothesis motivated by known failure modes reported
elsewhere in the literature (e.g., security weaknesses in LLM-generated code
have been documented by prior work such as CyberSecEval), but has not yet
been independently measured by this project's own pipeline. The immediate
priority before any submission-quality draft is closing that gap: running
real models through a real (if small) task set end-to-end.

## 7. Limitations (draft)

- Dataset scale: 10 prototype tasks vs. 1,800 planned.
- Security metric: regex heuristic vs. planned multi-scanner pipeline.
- No real model has been evaluated end-to-end yet; all "expected results"
  are hypotheses carried from the design phase.
- No human-expert labeling (CWE risk, gaming vectors) has been performed.

## 8. Target Venue

ICSE 2027 / FSE 2027, per DESIGN_DOC.md timeline. Given current
implementation status, a realistic interim target is a workshop paper or
arXiv preprint once Experiments 0-1 have real-model measurements, with the
full ICSE/FSE submission following Experiments 2-5.
