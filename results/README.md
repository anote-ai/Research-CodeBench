# results/

This directory holds **actual output artifacts** from running code in this
repository — not hand-written or hypothesized numbers.

## Current contents

- `exp0_baseline.json` — produced by `experiments/exp0_baseline.py`. It
  records real pass@1 / pass@5 / security_score values from actually
  executing the 10 reference solutions in `src/codebench/data.py` against
  small generated test cases for each task. Because these are reference
  (presumed-correct) solutions rather than model-generated code, the
  pass rates are expected to be high; the point of this artifact is to
  prove the execution + scoring pipeline runs end-to-end on real code, not
  to make a claim about any model's coding ability.

## What is intentionally NOT here yet

- Any SSR/SGR/CIR numbers for GPT-4o, Claude, Gemini, or other systems
  listed in DESIGN_DOC.md's "Systems Under Evaluation" table. Those numbers
  do not exist anywhere in this repository; DESIGN_DOC.md's "Expected
  Results" tables are explicitly hypotheses, not data, and PAPER_DRAFT.md
  re-labels them as such.
- A populated `data/tasks/` directory (1,800 tasks). Only the 10 prototype
  `SAMPLE_TASKS` exist today, in `src/codebench/data.py`.

## Convention going forward

When a new experiment script under `experiments/` is implemented and run
against a real model, its output should be written here as
`<experiment_name>.json` (or `.csv`), and PAPER_DRAFT.md's corresponding
section should be updated from "(projected, pending full experiment run)"
to "(measured)" with a pointer to the artifact and the commit/run that
produced it.
