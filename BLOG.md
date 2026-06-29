# Why "Pass@1" Is Lying to You About Your AI Coding Assistant

*A plain-language summary of the CodeBench project. For the full technical design, see [DESIGN_DOC.md](./DESIGN_DOC.md). For paper-style framing, see [PAPER_DRAFT.md](./PAPER_DRAFT.md).*

## The one-sentence pitch

Your AI coding assistant might pass 90% of its tests and still be writing code
full of SQL injection bugs, gamed test cases, and snippets that don't actually
fit into your real codebase — and the industry's favorite metric, "pass@1,"
has no way of telling you that.

## The problem, in plain English

Every time a new model comes out, someone publishes a leaderboard number like
"GPT-4o gets 90% on HumanEval." That number answers exactly one question: did
the generated code pass the unit tests it was given? It does **not** answer:

- Did the code introduce a security vulnerability while passing those tests?
- Did the model actually solve the problem, or did it find a shortcut that
  satisfies a weak test suite without doing the real work (e.g. hardcoding
  the expected output)?
- Would this code actually work if you dropped it into a real, messy,
  pre-existing repository instead of a blank file?
- Is the model's high score because it's smart, or because it has memorized
  this exact problem from its training data?

CodeBench is a proposed benchmark designed to answer all four questions at
once, instead of just the first one.

## What we're building

Three new numbers, layered on top of ordinary pass@1:

1. **SSR (Security Safety Rate)** — of the solutions that pass their tests,
   what fraction are also free of known vulnerability patterns (SQL
   injection, unsafe deserialization, command injection, etc.)?
2. **SGR (Specification Gaming Rate)** — of the solutions that pass their
   tests, what fraction are actually *wrong* once you check them against a
   stricter "did you really solve the stated problem" oracle?
3. **CIR (Codebase Integration Rate)** — when the same task is embedded in a
   real, existing repository instead of a blank file, how much does the
   pass rate drop?

The hypothesis driving this work (see DESIGN_DOC.md Experiments 1-3) is that
all three numbers will reveal a meaningful gap between "looks good on a
leaderboard" and "safe to ship into production." Until that gap is measured
on real model outputs, it remains a hypothesis, not a result.

## What exists today vs. what's still ahead

This is an honest status update, not a result announcement.

**What's built:** a data-model and scoring harness (`src/codebench/`) with
`CodeTask`, `AgentSubmission`, `ExecutionResult`, `TestSuite`, and
`ComplexityScore` objects; metrics for pass rate, pass@k, regression rate,
tool efficiency, cost-adjusted score, a regex-based security heuristic, and a
complexity-adjusted correctness score. All of it is unit tested
(`tests/`). We've also added `experiments/exp0_baseline.py`, the first
script that runs the harness against *real* reference-solution code
(actually executing it) rather than only random numbers — see
`results/README.md` for what that script does and does not prove.

**What's still synthetic:** the bulk of the harness's example data is
*generated* — `make_benchmark`, `make_rollout_benchmark`, and
`make_test_suite` in `src/codebench/data.py` produce seeded-random pass
rates, not the output of any real model run against a real task. The 1,800
task dataset, the Semgrep/Bandit/CodeQL scanner integration, and the
semantic-gaming oracle described in DESIGN_DOC.md are designed on paper but
not yet implemented in code.

**What that means concretely:** every leaderboard number you'd see from
`python scripts/run_demo.py` is a number about the test harness's random
number generator, not about GPT-4o, Claude, or any other real coding
assistant. That's a fine and useful thing to have — it lets us validate the
scoring logic before spending API budget — but it is not yet a research
result. `experiments/exp0_baseline.py` is a first, small step away from
that: it runs genuine Python execution against the 10 hand-written sample
tasks' reference solutions, so its pass-rate numbers are real (if trivial,
since reference solutions are expected to pass their own tests).

## What's next

The path from "harness with synthetic data" to "the SSR/SGR/CIR numbers in
DESIGN_DOC.md" is, in order:

1. Build a small (~50-100 task) real task set with actual functional tests,
   replacing the synthetic generators for at least one experiment.
2. Wire up one real model (even a single API) end-to-end: prompt → generated
   code → real pytest execution → real pass/fail, instead of seeded RNG.
3. Add a real static-analysis security scan (Bandit is the easiest first
   step; it's a pure-Python AST scanner with no external service
   dependency) and compare against the current regex heuristic in
   `evaluate.py`.
4. Only then start reporting SSR/SGR/CIR numbers for real systems.

We'll publish an update once Experiment 0 (the baseline replication
experiment in DESIGN_DOC.md) has been run against a real model rather than
synthetic or reference-solution data.
