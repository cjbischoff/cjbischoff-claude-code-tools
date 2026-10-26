---
type: how-to-guide
title: Running a sec-overlay Audit
description: The deterministic smoke-scan command versus a full agentic audit, the /sec-overlay:audit slash command and GitHub composite Action entrypoints, the diff-scoped review mode, preflight tool checks, environment prerequisites, and how the harness upholds its never-execute-the-target invariant.
tags: [sec-overlay, running-audit, preflight, smoke-scan, review-mode]
---

# Running a sec-overlay audit

There are several ways to run this harness, all built on the same deterministic core and
[pipeline](pipeline.md): a fast **smoke scan** with no agents, the **full agentic audit** driven
either manually or through the `/sec-overlay:audit` slash command, and a lighter **diff-scoped
review** mode consumed directly by a GitHub composite Action. All start from
`skills/sec-overlay/helpers/` — inside an installed plugin, that is
`${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/helpers`.

## Quick deterministic smoke scan (no agents)

```bash
cd skills/sec-overlay/helpers
uv run python -m sec_overlay.cli scan \
  --target <path-to-code> \
  --workspace <path-to-output-workspace> \
  --config rules/smoke.yaml \
  --sha "$(git -C <path-to-code> rev-parse HEAD)"
```

This runs `sec_overlay.cli.run_scan`: semgrep → `normalize()` → stamp `discovery_sha` on every
finding → write `findings/F-*.json` → emit `report.sarif` + `report.md` + `state.json` →
`record_stage(ws, "prefilter")`. **It runs only the semgrep backend** — CodeQL, SCA
(`osv-scanner`), and secrets scanning are not invoked, unlike the full pipeline's
[prefilter phase](pipeline.md#the-full-phase-order-28-phase_table-entries), which runs all four concurrently. It also
never calls `sec_overlay.state.begin_pass`, so it does not pin a SHA or advance the campaign's
`pass_number` — a smoke scan is a one-shot prefilter run, not a pass in the multi-pass campaign
model described in [pipeline](pipeline.md#multi-pass-campaigns). It is the fast path to see
output — **not** a real audit: no agents run, so there is no investigate gate ladder, no
adversarial validation, and no `risk_score`. The bundled `rules/smoke.yaml` is a minimal
ruleset; the vendored, gitignored semgrep-rules clone (`helpers/rules/semgrep/`) is **not** part
of the plugin — for a real audit, point `--config` (and the recon agent's `rulesets`) at your
own semgrep ruleset. `.github/workflows/sec-overlay-tests.yml` runs this exact command as an
offline smoke-scan check against a committed fixture on every PR that touches `helpers/`.

## Full agentic audit — manual walkthrough

The main agent orchestrates the entire phase order in [pipeline](pipeline.md), substituting
path/scope tokens before spawning each subagent (`{{TARGET}}`, `{{WORKSPACE}}`,
`{{OVERLAY_ROOT}}`, `{{HELPERS_DIR}}`, `{{REPO_ROOT}}`, `{{SCAN_SCOPE}}`, `{{ATTACK_CLASS}}`,
`{{PHASE}}`, `{{ROUND}}`). Every agent's final return is persisted with
`workspace.record_agent_return(ws, "<agent-label>", <text>)` (→ `runs/<agent>.txt`) and read
back with `read_agent_return` — the orchestrator never depends on a subagent's chat summary
propagating; disk state is the source of truth. If a host hard-blocks a subagent's Write tool
on a `findings`/`report`/`summary`-like path, the `OUTPUT_WRITE_FALLBACK` prompt-constants
block instructs writing via a `python3 shutil.copy` from a temp file instead, so a blocked
write never silently loses a finding.

## The sec-overlay audit slash command (a driver-backed shortcut)

`plugins/sec-overlay/commands/audit.md` is a thin routing document, not executable logic: it
tells the invoking agent how to drive a single-repo audit (or several, correlated) through
`sec_overlay.run`/`sec_overlay.driver` rather than walking `SKILL.md`'s phase list by hand.

```
/sec-overlay:audit <repo> [<repo> ...]
```

**One repo:**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -c "from sec_overlay.run import drive; print(drive('<repo>', config='rules/smoke.yaml'))"
```

`run.drive()` writes `run.env` once, pins the pass SHA, and before each deterministic stage
fences the tree against the pass baseline (`run.fence()` raises `WorkingTreeFenceError` if the
audited tree changed mid-run) and writes a receipt. When it prints a `NEXT AGENT PHASE` block,
run that agent prompt so it writes its declared outputs, then close the phase:

```bash
uv run python -c "from sec_overlay.run import advance; advance('<repo>', '<phase>')"
```

`advance()` fences the tree, writes the receipt, and records the stage before the agent sees
the next `drive()` call continue the sequence. Resume is stage-based: `drive` picks up at the
first phase with no recorded stage — the same `PHASE_TABLE`/`record_stage` contract the manual
walkthrough uses, just invoked through `sec_overlay.driver.run_audit`/`AuditContext` instead of
by hand. **Two or more repos** additionally infer each repo's correlation role from its own
`kb/scan-profile.json` (`run.infer_role`), confirm with the operator before writing anything,
then synthesize a manifest and hand off to
[cross-repo correlation](cross-repo-correlation.md)'s `python -m sec_overlay.correlate`.

## The GitHub composite Action for CI diff review

`plugins/sec-overlay/action.yml` is a composite Action a consumer repository's workflow can call
directly: it runs `sec_overlay.cli review` over a pull request's base/head diff, uploads the
resulting `report.sarif` to code scanning if one was produced, and posts findings as a pull
request review via `sec_overlay.pr_poster` (critical/high inline, the rest in the summary). The
review event is always `COMMENT`, so this path never blocks a merge on its own — same
advisory-only posture as [CodeRabbit](../../governance/code-review.md). It exposes `base`/`head`
(default to the PR's own), `profile` (`security` default or `general`), and a required
`github-token` with pull-requests write.

## Diff-scoped review

```bash
cd skills/sec-overlay/helpers
uv run python -m sec_overlay.cli review \
  --base <base-ref> --head <head-ref> --root <path-to-code> \
  --profile security   # or: general
```

Review mode has no phase driver like the full audit above — it is a multi-step loop the main
agent runs directly, over one `review-file` subagent per reviewable file, plus a retract-only
**reflection** pass:

1. **Prepare** — `... review --base <ref> --prepare` writes `runs/review_plan.json` (one entry
   per reviewable file: path, resolved rule text, diff, other changed files, and sibling-bundle
   diffs for impl/test or locale/config pairs) and renders one `agents/review-file.md` prompt
   per entry under `runs/review_prompts/<slug>.md`. A unit over `PLAN_LINE_THRESHOLD` (100)
   lines first gets an advisory `agents/review-plan.md` pass.
2. **Dispatch** — spawn a `review-file` subagent (sonnet) per entry in waves of three to four,
   persist each final return with `workspace.record_agent_return`, never exceed
   `--concurrency` (default 8, ceiling 128) live subagents at once.
3. **Prepare reflection** — `... review --base <ref> [--profile general] --prepare-reflection`
   reads the recorded returns, runs the position gate and `apply_profile`, and for each file
   with kept findings renders an `agents/review-filter.md` prompt (path, diff, kept findings —
   no severity/category, so the filter has nothing to rank or rewrite) under
   `runs/reflection_prompts/`.
4. **Dispatch reflection** — spawn a `review-filter` subagent per plan entry, persist its
   verdict envelope (`{"base", "head", "verdict"}` — the base/head pair guards against consuming
   a verdict captured for a different diff).
5. **Consume** — `... review --base <ref> [--profile general] [--model <id>]` reads both
   recorded review returns and reflection verdicts back from disk and runs the full gate chain:
   position gate → `apply_profile` → the reflection filter (`apply_verdict`, retract-only; a
   hardcoded `PROTECTED_SUBJECT_CLASSES` veto refuses a retraction naming a protected-subject
   finding, still recorded rather than silently dropped) → the receipt gate.

`--profile security` (the default) reproduces the pre-review-mode gate ladder byte-for-byte —
every finding gates A-E (`EXCLUSION_RULES`) mark is dropped. `--profile general` relaxes gates A
and B for a finding whose rule-doc defect class is one of `null-dereference`, `thread-safety`,
`resource-leak`, `error-swallowing`, `injection` (`GENERAL_PROFILE_EXCLUSION_RULES`) — a strict
superset of the security profile's output, never a change to it. Exit 0 on a `complete` coverage
seal, 2 on an invalid ref/unsafe rule file/resumed-run identity mismatch, 3 when one or more
files could not be reviewed. The loop fails open at every stage: a file with no recorded return
or verdict, or one whose return won't parse, contributes zero findings for that file and is
listed in the run's skip ledger rather than aborting the pass.

Every review artifact (`coverage_manifest.json`, `runs/review_plan.json`, `report.md`,
`review_ledger.json`, `artifacts/review_result.json`) resolves under the same per-repo memory
sidecar (`<root>/.sec-overlay/<repo-slug>/`), never at `--root` itself. `review` takes an
optional `--workspace` override mirroring `scan`/`audit`; whichever branch applies, pass the
**identical** value to every `prepare`, dispatch, and `consume` invocation of one review — the
sidecar slug derives from it, so a different spelling silently orphans the prepared run. Pass
the identical `--model` string to every invocation the same way — a resumed run with a different
`--model` or `--profile` is rejected (exit 2), never silently mixed. Background developer
context (`--background`/`--background-file`) is sanitized (`sec_overlay.background`, 1 MB cap,
secret-abort, envelope-wrapped) before it reaches the review prompt as orientation only.

## Preflight — the first gate

```bash
uv run python -m sec_overlay.preflight
```

`helpers/sec_overlay/preflight.py`'s `check_tools()` checks for **seven** binaries: `semgrep`,
`rg`, `codeql`, `tree-sitter`, `ast-grep`, `osv-scanner`, `gitleaks`. Three of them —
`tree-sitter`, `osv-scanner`, `gitleaks` (the `_OPTIONAL` set) — are **optional**: a scan
degrades gracefully and logs them as skipped rather than crashing preflight. The other four —
`semgrep`, `rg`, `codeql`, `ast-grep` — are required backends: `rg` is required because
`route-census` (the first deterministic phase of every audit) and `structural_index` both shell
out to it, so a missing `rg` must fail preflight, not a mid-run phase. `preflight`
prints the exact install command for anything missing. **It never installs — the operator runs
the printed commands.**

The report it prints also lists which **CodeQL query packs** are installed. This is the sharpest
edge in the whole setup: **the `codeql` binary being present does not mean the per-language
query packs exist**, and a missing pack silently drops all of that language's dataflow
coverage. If a language you will scan is not listed, run
`codeql pack download codeql/<lang>-queries` first
(`preflight.codeql_pack_download_cmd(langs)` prints the exact command for any language set).

**A scan is clean only if every planned backend actually ran.** `run_prefilter` returns
`{candidates, backends_run, skipped, failed, excluded, dropped_nonsecurity, skipped_reasons}`;
STOP and surface a setup error if `backends_run` is empty, or any planned backend appears in
`failed` / `skipped_reasons` (e.g. `codeql: pack-missing`). A partial scan — semgrep ran, codeql
failed — is a **coverage hole, not "no findings"**; never report it as clean. This rule is
stated identically in `SKILL.md` and the skill's own [`CLAUDE.md`](/plugins/sec-overlay/skills/sec-overlay/CLAUDE.md) §3.

## Environment prerequisites for a full run

A clean checkout is missing one thing a full audit needs — the bench corpus that used to be a
second gap now **ships committed**:

1. **The vendored semgrep ruleset.** `helpers/rules/semgrep/` is a **gitignored, shallow-cloned
   directory** — there is no `.gitmodules` file in this repository, so it is **not** a git
   submodule despite some older docs' claims. Seed it with the exact command `preflight` prints:
   `git clone --depth 1 https://github.com/semgrep/semgrep-rules helpers/rules/semgrep`. Without
   it, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` fails for lack of
   rules — this is the **one remaining env-only test failure** on a clean checkout.
2. **External tool binaries.** `uv run python -m sec_overlay.preflight` must show semgrep, `rg`,
   codeql (+ language packs), ast-grep present (osv-scanner/tree-sitter/gitleaks are optional).
3. **The bench corpus ships committed.** `bench/corpus_seed/*.json` holds only public entries
   (public-app advisories pinned to a commit, dep-CVE lockfiles, synthetic fixtures under
   `helpers/fixtures/`) and is tracked in git — `test_bench.py::test_seed_corpus_is_valid`,
   `test_seed_corpus_has_min_entries`, and `test_citations.py::test_all_mapped_ids_exist_in_seed`
   now run in CI, not just locally. The corpus is still **dev/bench only** — a grading oracle,
   never part of an audit run. See
   [developing the skill](developing-the-skill.md#the-bench-harness-dev-only-not-part-of-an-audit).

**The one env-only failure on a clean checkout is environmental, not a code defect** — do not
"fix" it by committing the vendored ruleset content:
`tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`. The skill
`CLAUDE.md` §1 states this explicitly.

## The do-not-execute-the-target invariant

The harness never runs or modifies the reviewed source, with exactly one documented, opt-in
exception: the `prove` phase (#24 in [pipeline](pipeline.md)) may execute target-derived code,
and only when `scan_options.prove_findings` is true — absent by default, so a normal audit never
runs it. All building and running happen out of tree under `ws.repro`, so the target working
tree stays untouched. A proof promotes a finding to `confirmed` only when the agent drove a real
entrypoint (`scope: entrypoint`), the class has a wrapper-decidable oracle, and the oracle
observed the effect; anything weaker records a degradation and leaves the finding where it was.
See `docs/decisions/2026-08-31-prove-lane-execution.md` for the three conditions a proof must
satisfy and the rejected alternatives. Patch verification (`verify`, phase #19) also touches
execution-adjacent ground — it applies a `patch_diff` to a **throwaway copy** and re-scans that
copy, never the real target, and the red-team plan it ultimately feeds is a manual test plan a
human runs, not something the harness executes itself.
