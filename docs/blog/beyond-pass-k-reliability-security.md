# Beyond Pass@k: Measuring Reliability and Security of AI Coding Agents

*How a subtle misuse of a good estimator inflates coding-agent leaderboards — and what to measure instead.*

---

If you follow AI coding agents, you have seen the numbers: benchmark after benchmark reporting `pass@k` scores in the high 0.9s. Some of those numbers are measuring something real. But in some agentic benchmark implementations, the number is an artifact of *how the metric is computed*, not of how good the agent is.

The short version: `pass@k` was designed to summarize many **independent attempts** at a task. Some agentic benchmarks instead feed it the **unit tests inside a single attempt**. Those are very different things, and the substitution quietly turns "how many tests passed" into "how reliable is this agent" — two questions with very different answers.

This post summarizes our paper, *Beyond Pass@k: Measuring Reliability and Security of Agentic Code Generation*, which diagnoses the error, proposes a corrected metric we call `reliability@k`, and reports an initial real-world data point from SWE-bench Verified.

## The problem with `pass@k`

The `pass@k` estimator comes from the Codex paper (Chen et al., 2021). It answers a specific question: *if I draw `k` independent samples from a model, what is the probability that at least one is correct?* To reduce variance, you generate `n ≥ k` samples, count the `c` correct ones, and plug both into an unbiased combinatorial formula.

The formula is fine. Its assumptions are the point: the `n` inputs must be **independent, identically distributed attempts** at the task. For short HumanEval-style completions, that's exactly what you have — sampling 10 completions of a 15-line function is cheap, and each one is a genuine independent draw.

Agentic, repo-level benchmarks are a different world. A full agent run is expensive: tool calls, file edits, test runs, minutes of wall-clock time. Faced with that cost, some implementations quietly redefine the inputs:

- `n` becomes the **number of unit tests** in one submission,
- `c` becomes the **number of those tests that passed**.

But the unit tests inside one submission are not independent attempts. They are correlated sub-results of a *single* attempt — one generated solution, executed once. If the solution is 40% right, the tests don't represent 40 independent successes out of 100 tries; they represent one try that got a partial grade.

The practical consequence: the score now depends on **test-suite size**. A task with 40 tests and a task with 10 tests produce different `pass@k` values for agents of *identical* ability — the metric measures the benchmark's plumbing, not the agent.

## Our fix: `reliability@k`

`reliability@k` is not a new estimator. It is the *same* Chen et al. formula with the inputs it was designed for:

- `n` = number of **independent rollout attempts** — full, fresh runs of the agent on the task,
- `c` = number of rollouts that **fully succeed** (every test passes).

The unit of measurement moves from "an individual test" to "a complete task attempt." That matches what a user of a coding agent actually experiences: an engineer doesn't run an agent fifty times and cherry-pick; they run it once and need the whole task to be done. `reliability@k` estimates the probability that at least one of `k` deliberate, independent attempts fully solves the task.

## What we found

We tested four hypotheses on the CodeBench framework — a synthetic multi-rollout benchmark (10 tasks × 3 agent profiles × 8 rollouts, fixed seed) for H1–H3, plus a live-API experiment for H4.

| Experiment | Question | Result |
|---|---|---|
| **H1** | Does test-suite size alone change the broken score? | **Yes.** Two submissions with the *same* 40% test pass rate scored 0.976 vs 1.000 on broken `pass@5` — the only difference was the number of tests. |
| **H2** | How big is the inflation? | **Large.** Broken `pass@5` overstated corrected `reliability@5` by 0.85–0.97 absolute; reported scores of 0.96–0.98 became 0.00–0.12 when corrected. |
| **H3** | Can one cheap rollout + a proxy substitute for repeated runs? | **No.** A proxy combining pass rate, regression penalty, and tool efficiency correlated with `reliability@5` at only Spearman ρ = 0.417 — below our 0.70 usefulness bar. |
| **H4** | Does security screening change agent rankings? | **Not in this run.** We proposed `security_adjusted_reliability@k` (only rollouts that are both correct *and* free of high-severity insecure patterns count). In an initial live-API test with three agents, the adjusted score was identical to the unadjusted one for every agent — no ranking change. With only 3 agents and a lenient threshold, this test was under-powered; the metric remains a proposed lens, not a confirmed effect. |

Two honest caveats belong next to that table. First, in our synthetic runs the *ranking order* of agents happened to survive the correction — what changed radically is the absolute meaning of the scores ("nearly perfect" → "rarely completes the whole task"). Second, H4's null result is not evidence that security doesn't matter; it is evidence that our first, small test couldn't detect an effect if one exists.

## Real-world pilot: SWE-bench Verified

Synthetic experiments demonstrate estimator behavior, but the obvious question is whether the pass-rate-vs-resolution gap shows up on real tasks. As a first, deliberately small check, we ran a **preliminary pilot** on [SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified): the first 5 deterministic instances of the test split (all from `astropy/astropy`), one attempt per task by the Claude Code CLI in a restricted mode (file edits allowed, no shell execution — so no self-testing), with patches judged by the **official SWE-bench harness** in Docker. The agent saw only the issue text, repo, and base commit; leakage checks confirmed no gold patches or hidden test names reached it.

| Task | Difficulty | Resolved | Hidden tests passed | Regressions |
|---|---|---|---|---|
| astropy-12907 | medium | ✅ | 15/15 | 0 |
| astropy-13033 | medium | ❌ | 20/21 | 0 |
| astropy-13236 | medium | ❌ | 644/646 | 0 |
| astropy-13398 | hard | ❌ | 63/72 | 5 |
| astropy-13453 | medium | ❌ | 2/10 | 7 |

Headline numbers:

- **1/5 resolved** → `reliability@1` = **0.20**
- Macro-averaged hidden-test pass rate = **0.8049**
- Macro-averaged regression rate = **0.1539**

That gap is the whole story in miniature. Scored on partial test pass rates, this agent looks ~80% capable on these tasks. Scored on the question that matters — *was the issue actually fixed?* — it's 20%. Look at rows two and three: 20/21 and 644/646 hidden tests passing, zero regressions, and still **not resolved**, because the one behavior change the issue asked for wasn't there. A partial pass-rate metric grades those attempts as excellent. Meanwhile the last two rows show the opposite failure: plausible patches that quietly broke 5 and 7 previously-passing tests.

To be explicit about scope: **this is a pilot, not a SWE-bench benchmark.** Five tasks, one repository, one agent, one attempt each. It cannot support `reliability@3` or `reliability@5` claims (those need multiple independent attempts per task), and it doesn't rank anything. What it provides is a real-repository data point consistent with the concern H1 and H2 demonstrate synthetically.

## Why this matters

**Leaderboards can overstate reliability.** If a benchmark computes `pass@k` from test counts, its top-line numbers inflate with test-suite size. Anyone comparing agents across such a leaderboard is partly comparing test suites.

**Users care about task resolution, not test fractions.** An enterprise adopting a coding agent experiences task-level outcomes: the bug is fixed or it isn't, and nothing else broke. A metric that awards 0.98 to an agent that rarely completes an entire task is answering the wrong question.

**Repeated attempts are expensive — and necessary.** H3 says you can't shortcut it with a one-rollout proxy. Multi-rollout evaluation costs real money for agentic systems, but it is currently the only trustworthy way to estimate task-level reliability.

**Passing tests ≠ safe code.** Industry data (Veracode, 2025) reports that AI-generated code carries substantially more vulnerabilities than human-written code. Our `security_adjusted_reliability@k` is one attempt to fold that into rankings; the initial test was inconclusive, but the blind spot it targets is real.

## Limitations

- The core H1–H3 results come from a **synthetic** benchmark, built to stress-test estimator behavior — not from production agents in the wild.
- **H4 covered only three agents**, with a heuristic 7-pattern security scanner and a single lenient threshold we did not sweep. Its null result is under-powered, not definitive.
- The **SWE-bench pilot is 5 tasks, one repo, one agent, one attempt per task**, with the agent unable to run tests on its own work. It supports `reliability@1` only — no `reliability@3` or `reliability@5` claims — and does not represent a full SWE-bench evaluation.

## Takeaway

`pass@k` is not wrong. Using it with the wrong `n` and `c` is wrong. The estimator needs independent attempts; unit tests inside one submission aren't that, and treating them as if they were converts test-suite size into fake reliability.

For agentic coding systems, benchmarks should measure **independent task-level rollouts** and report `reliability@k` — the same math, pointed at the right unit: the complete task attempt. Our synthetic results show how large the gap can be (0.96–0.98 vs 0.00–0.12), and a small SWE-bench Verified pilot suggests the same pattern holds on real repository tasks (0.80 test pass rate vs 0.20 resolution).

The next steps are the obvious ones: scale real-world evaluation to multi-attempt, multi-repository runs that can support `reliability@k` for k > 1, broaden the agent pool, and give the security-adjusted metric the better-powered test it needs.

---

*The paper (`paper/sigconf.tex`), the pilot notes (`docs/swebench_pilot_results.md`), and the converted pilot metrics (`data/swebench_results_claude-code_smoke-v1.json`) are in this repository. The SWE-bench pipeline used for the pilot — adapter, runner, and results conversion — lives in `src/codebench/` with usage docs in `docs/swebench_experiment.md`.*
