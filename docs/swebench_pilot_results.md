# SWE-bench Verified 5-Task Pilot Results (smoke-v1)

**Date:** 2026-07-13 · **Run id:** `smoke-v1-five-tasks` · **Status:** frozen

> **Scope disclaimer.** This is a 5-task pilot / smoke experiment validating the
> CodeBench → SWE-bench pipeline end-to-end. It is **not** a paper-level
> benchmark and does not prove the full method: the sample is tiny (n=5),
> single-repo, and single-attempt. What it provides is **real-world evidence
> consistent with our synthetic H1/H2 concern** that per-test pass rates
> substantially inflate apparent capability relative to strict task resolution.

## Experiment setup

- **Dataset:** [SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified),
  first 5 instances of the test split (deterministic sample via
  `scripts/prepare_swebench_sample.py --limit 5`).
- **Pipeline:** `scripts/run_swebench_agent.py` (PR #31) — agent-safe task
  loading, isolated git worktree per attempt at the instance `base_commit`,
  `git diff` captured as `model_patch`, official prediction JSONL export.
- **Leakage policy verified:** prompts contained only the issue text, repo
  name, base commit, and difficulty. Content-level checks confirmed 0 gold
  patch lines and 0 hidden test names in any agent input; overlap between
  agent patches and gold patches in *outputs* reflects independent fix
  convergence, not leakage.
- **Evaluation:** official SWE-bench harness (`swebench` 4.1.0), Docker
  29.6.1 (linux/aarch64), all 5 containers completed with no errors.

## Task list

All five instances are from `astropy/astropy` (a known limitation, see below):

| Instance | Difficulty |
|---|---|
| astropy__astropy-12907 | medium |
| astropy__astropy-13033 | medium |
| astropy__astropy-13236 | medium |
| astropy__astropy-13398 | hard |
| astropy__astropy-13453 | medium |

## Agent configuration

- **Agent:** Claude Code CLI v2.1.185, headless (`claude -p`), invoked as
  `model_name_or_path = claude-code`.
- **Permission mode:** `acceptEdits` — the agent could read the repo and edit
  files but **could not execute shell commands**, i.e. it could not run the
  project's tests to verify its own fix before submitting.
- **Attempts:** 1 per task (no rollout variance). **Timeout:** 1800 s per
  attempt (none hit; the hard task used 878 s, the mediums 64–128 s).

## Harness command

```bash
.venv/bin/python -m swebench.harness.run_evaluation \
    --dataset_name SWE-bench/SWE-bench_Verified \
    --predictions_path predictions/smoke-v1-five-tasks_attempt1.jsonl \
    --max_workers 2 \
    --run_id smoke-v1-five-tasks \
    --instance_ids astropy__astropy-12907 astropy__astropy-13033 \
        astropy__astropy-13236 astropy__astropy-13398 astropy__astropy-13453
```

Converted to CodeBench metrics with:

```bash
.venv/bin/python scripts/convert_swebench_report.py \
    --run-ids smoke-v1-five-tasks --model-name claude-code -k 1 \
    --output data/swebench_results_claude-code_smoke-v1.json
```

## Results

| Instance | Patch | Applied | Resolved | FAIL_TO_PASS | PASS_TO_PASS | Regressions |
|---|---|---|---|---|---|---|
| astropy__astropy-12907 | 506 B | ✓ | **✓ resolved** | 2/2 | 13/13 | 0 |
| astropy__astropy-13033 | 1.2 KB | ✓ | ✗ | 0/1 | 20/20 | 0 |
| astropy__astropy-13236 | 725 B | ✓ | ✗ | 0/2 | 644/644 | 0 |
| astropy__astropy-13398 | 7.8 KB | ✓ | ✗ | 0/4 | 63/68 | 5 |
| astropy__astropy-13453 | 379 B | ✓ | ✗ | 0/1 | 2/9 | 7 |

All five attempts produced non-empty, cleanly-applying patches; every failure
was a hidden-test outcome, not an infrastructure error.

**Headline metrics** (see `data/swebench_results_claude-code_smoke-v1.json`):

| Metric | Value |
|---|---|
| reliability@1 (strict resolution) | **0.20** |
| Mean hidden-test pass rate | **0.8049** |
| Mean regression rate | **0.1539** |

## Key interpretation

The central observation is the **4× gap between mean test pass rate (0.80) and
strict task resolution (0.20)** on real tasks. A leaderboard scored on
per-test pass rates would report this agent as "80% capable" on these tasks,
while the ground-truth resolution rate is 20%. This mirrors — with real
rollouts instead of synthetic ones — the inflation our H1/H2 experiments
demonstrated: operationalizing pass@k on within-submission test counts
overstates reliability relative to rollout-based reliability@k.

Failure modes split into two classes, both instructive:

1. **Near-misses** (13033, 13236): zero regressions and near-perfect pass
   rates, but the specific required behavior change absent or subtly wrong.
   These are precisely the cases a pass-rate metric scores as excellent.
2. **Regressive fixes** (13398, 13453): plausible edits that broke 5 and 7
   existing tests respectively — invisible to any metric that does not run
   the full hidden suite, and a direct motivation for tracking
   `regression_count` as a first-class signal.

## Limitations

- **n=5 tasks, one repo** (astropy) — no cross-repo generalization claims.
- **1 attempt per task** — reliability@1 only; no rollout variance, so this
  does not yet exercise the reliability@k estimator for k>1.
- **Agent could not self-test** (`acceptEdits` blocks shell execution). Both
  near-misses might convert with test-driven iteration; the pilot measures a
  deliberately restricted configuration.
- Single agent, single prompt template, default temperature/settings.

## Next steps

1. **Multi-attempt runs** (`--attempts 3` or 5) to compute real
   reliability@k with k>1 and observe per-task rollout variance.
2. **Permission mode allowing test execution**, to measure how much
   self-verification closes the near-miss gap.
3. **Broader sample** — 30–50 tasks across multiple repos
   (`prepare_swebench_sample.py --limit 30/50`).
4. Additional agents for a comparative leaderboard, feeding the existing
   `codebench.evaluate` machinery.

## Artifacts

| Artifact | Path | In git? |
|---|---|---|
| Converted CodeBench results | `data/swebench_results_claude-code_smoke-v1.json` | yes (safe: aggregates + per-task counts only) |
| Prediction JSONL | `predictions/smoke-v1-five-tasks_attempt1.jsonl` | gitignored |
| Harness summary | `claude-code.smoke-v1-five-tasks.json` | gitignored |
| Per-instance harness logs | `logs/run_evaluation/smoke-v1-five-tasks/claude-code/` | gitignored |
| Per-attempt records (prompt/log/patch) | `attempts/smoke-v1-five-tasks/` | gitignored |
