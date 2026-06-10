# CodeBench — Research Design Document

## Goal

Build the first code generation benchmark that jointly evaluates functional correctness, security vulnerability rate, and specification compliance — the three dimensions that determine whether AI-generated code is safe to ship, not just whether it passes tests.

## Objective

1. Create a benchmark of 500+ coding tasks spanning 5 languages and 4 task categories (algorithms, data processing, API integration, security-sensitive systems code)
2. Measure pass@k, security_score, and specification_compliance_rate for 8+ leading code models
3. Produce the definitive contamination analysis for current code benchmarks

## Background / Motivation

HumanEval (2021) has two critical flaws: (1) it measures only functional correctness on toy algorithmic tasks, not security or specification compliance; (2) it is heavily contaminated — models trained on GitHub have seen most HumanEval problems.

Meanwhile, AI coding tool usage has exploded: GitHub Copilot has 1.8M+ subscribers; Claude Code now writes 80%+ of Anthropic's own code. Security and correctness failures of these tools are increasingly consequential.

## Experimental Design

### Baseline Experiment

**Replicate HumanEval and MBPP pass@1 for GPT-4o, Claude Sonnet, Gemini Pro, and Codestral**

- Metric: pass@1 using the Chen et al. (2021) unbiased estimator (20 samples per problem)
- Purpose: verify evaluation infrastructure; confirm numbers match published benchmarks within ±2%
- Expected result: GPT-4o ~90%, Claude ~88%, Gemini ~87%, Codestral ~85%

### Test Experiment 1: Security Score on Realistic Tasks

Create 100 security-sensitive coding tasks (authentication, SQL construction, file I/O, subprocess calls, cryptographic operations). Evaluate functional correctness AND security score (CWE categories: injection, buffer overflow, path traversal, hardcoded secrets, insecure random). Use Semgrep + Bandit + LLM security review with expert validation.

**Expected result:** functional correctness ~85%+ across all models; security scores 40–60% — models generate working-but-insecure code on 30–50% of security-sensitive tasks

### Test Experiment 2: Specification Compliance vs. Specification Gaming

Create 50 tasks with underspecified requirements. Evaluate whether models ask for clarification, document assumptions, and handle edge cases a reasonable developer would expect.

**Expected result:** no model asks for clarification; models game underspecified tests on 25–40% of tasks

### Test Experiment 3: Contamination Analysis

For each benchmark problem, search for near-duplicates in The Stack and GitHub. Compute contamination-adjusted pass@k: performance on confirmed-clean vs. potentially-contaminated problems.

**Expected result:** published HumanEval leaderboard rankings shift significantly after contamination adjustment

## Expected Results

1. A benchmark of 500+ tasks with security and specification compliance evaluation
2. Contamination analysis for major code benchmarks and leading models
3. **Key finding:** "AI code models score 30–50 points lower on security than on functional correctness — the gap current benchmarks hide"
4. Leaderboard at `codebench.anote.ai` with all three dimensions

## Why This Matters / Why People Would Care

- **Developers using AI coding tools:** need to know the security risk profile, not just test-pass rates
- **Security researchers:** first systematic characterization of security failure rates across major models
- **AI companies:** security is currently uncharacterized; this benchmark gives them a credible arena to compete on it
- **Enterprises:** compliance and security teams need benchmarks that reflect production risk

## Timeline

| Month | Milestone |
|---|---|
| 1–2 | Task construction (500 tasks, security annotation, contamination analysis) |
| 3 | Evaluation infrastructure (security scanner integration, specification compliance rubric) |
| 4 | Baseline + test experiments |
| 5 | Analysis + leaderboard |
| 6 | Submission to ICSE 2027 |

## Related Issues

- Design doc GitHub issue: #21
- Target conferences: see issues labeled `conference-prep`
- Reproducibility package: see issues labeled `artifact-release`
