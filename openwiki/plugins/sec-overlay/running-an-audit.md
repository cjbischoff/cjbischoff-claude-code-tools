---
type: how-to-guide
title: Running a sec-overlay Audit
description: The deterministic smoke-scan command versus a full agentic audit, preflight tool checks, environment prerequisites and the two known env-only test failures, and how the harness upholds its never-execute-the-target invariant.
tags: [sec-overlay, running-audit, preflight, smoke-scan]
---

# Running a sec-overlay audit

There are two ways to run a full audit against this harness: a fast deterministic
**smoke scan** with no agents at all, and the **full agentic audit** described in
[pipeline](pipeline.md), most often driven through the `/sec-overlay:audit` slash command
below. Both start from `skills/sec-overlay/helpers/` — inside an installed plugin, that is
`${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/helpers`. A third, separate and lighter workflow,
diff-scoped **review mode**, is documented on its own page — see [review mode](review-mode.md).

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
[prefilter phase](pipeline.md#the-full-phase-order), which runs all four concurrently. It also
never calls `sec_overlay.state.begin_pass`, so it does not pin a SHA or advance the campaign's
`pass_number` — a smoke scan is a one-shot prefilter run, not a pass in the multi-pass campaign
model described in [pipeline](pipeline.md#multi-pass-campaigns). It is the fast path to see
output — **not** a real audit: no agents run, so there is no investigate gate ladder, no
adversarial validation, and no `risk_score`. The bundled `rules/smoke.yaml` is a minimal
ruleset; the semgrep-rules submodule (fuller semgrep coverage) is not part of the plugin — for
a real audit, point `--config` (and the recon agent's `rulesets`) at your own semgrep ruleset.

## The `/sec-overlay:audit` slash command

`commands/audit.md` is the installed plugin's slash-command entry point:
`/sec-overlay:audit <repo> [<repo> ...]`. It is a thin routing document over
`sec_overlay.run.drive()`/`advance()` (single repo) and `python -m sec_overlay.correlate`
(two or more repos) — all executable logic stays under `helpers/sec_overlay/`.

For one repo, `sec_overlay.run.drive('<repo>', config='rules/smoke.yaml')` writes `run.env`
once, pins the pass SHA, and — before each deterministic stage — fences the tree against the
pass baseline and writes a receipt. When it prints a `NEXT AGENT PHASE` block, the driving agent
runs that agent prompt, then closes the phase with `sec_overlay.run.advance('<repo>', '<phase>')`
(fences the tree, writes the receipt, records the stage) before re-invoking `drive` to continue.
Resume is stage-based: `drive` picks up at the first phase with no recorded stage — the same
`record_stage` contract the rest of this page describes.

For two or more repos, the command drives each repo's audit in turn, infers each repo's role
from its `kb/scan-profile.json` (`sec_overlay.run.infer_role`), confirms the repo count and
inferred roles with the operator, then synthesizes a manifest
(`sec_overlay.run.synthesize_manifest`) and runs `python -m sec_overlay.correlate` — see
[cross-repo correlation](cross-repo-correlation.md) for what that produces. A barrier whose
enforcer repo the operator did not include is emitted as a `coverage-gap`, never a clean result.

This slash command is the main agent's primary entry point for a full audit; [pipeline](pipeline.md)
documents the phase order `drive`/`advance` walks, and the diff-scoped [review mode](review-mode.md)
is a separate command (`sec_overlay.cli review`) this slash command does not drive.

## Full agentic audit

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

## Preflight — the first gate

```bash
uv run python -m sec_overlay.preflight
```

`helpers/sec_overlay/preflight.py`'s `check_tools()` checks for seven binaries: `semgrep`,
`rg` (ripgrep), `codeql`, `tree-sitter`, `ast-grep`, `osv-scanner`, and `gitleaks`. Three of
them — `tree-sitter`, `osv-scanner`, `gitleaks` (the `_OPTIONAL` set) — are **optional**: a scan
degrades gracefully and logs them as skipped rather than crashing preflight. The other four —
`semgrep`, `rg`, `codeql`, `ast-grep` — are required backends the scan depends on (`rg` backs
the code-derived route census and the structural symbol index, not just the recall adversary's
grep-style checks). `preflight` prints the exact install command for anything missing. **It
never installs — the operator runs the printed commands.**

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

A clean checkout is missing three things a full audit needs:

1. **The vendored semgrep ruleset.** `rules/semgrep/` is a gitignored, shallow-cloned
   directory, not a tracked git submodule:
   `git clone --depth 1 https://github.com/semgrep/semgrep-rules rules/semgrep`. Without it,
   semgrep has no vendored rules and
   `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` fails. The tracked
   `helpers/rules/absence/` first-party pack ships with the plugin regardless and is unaffected.
2. **External tool binaries.** `uv run python -m sec_overlay.preflight` must show semgrep,
   codeql (+ language packs), ast-grep, osv-scanner present.
3. **The bench corpus ships committed.** `bench/corpus_seed/*.json` holds only public entries
   (public-app advisories pinned to a commit, dep-CVE lockfiles, and synthetic fixtures under
   `helpers/fixtures/`) and is tracked, not gitignored — a confirmed vulnerability from private
   code must never be added to it. `test_bench.py::test_seed_corpus_is_valid`,
   `test_seed_corpus_has_min_entries`, and `test_citations.py::test_all_mapped_ids_exist_in_seed`
   therefore run in CI, not just locally. It is still a dev/bench grading oracle — never part of
   an audit run. See [developing the skill](developing-the-skill.md#the-bench-harness-dev-only-not-part-of-an-audit).

**A clean checkout's env-only test failures are environmental, not code defects** — do not
"fix" them by fabricating a vendored ruleset or committing a private-repo finding into the seed
corpus. `tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` is the
one named in this environment prerequisites section (missing vendored semgrep clone);
`helpers/README.md` documents two env-only failures in total on a clean checkout — see the
skill `CLAUDE.md` §1 for the current, authoritative list before treating any other failure as
environmental.

## The do-not-execute-the-target invariant

The harness never runs, builds, or modifies the code it is auditing. This holds at every phase
that touches code:

- **Static analysis only.** Every SAST backend (`sast.py`, `codeql.py`, `sca.py`, `secrets.py`)
  parses source or scans dependency manifests; none of them execute the target.
- **Patch verification uses a throwaway copy.** `helpers/sec_overlay/verify.py` copies the
  target, applies the proposed `patch_diff` with `git apply`, re-runs the SAST on **the copy**,
  and compares pre/post presence of the finding's class. The original target is never modified.
  The comparison resolves to one of four outcomes: flagged pre-patch and gone post-patch →
  `status: fixed`, `verification: verified-static` (the only outcome that promotes a finding to
  `fixed`); the patch applies cleanly but the same class of hit still fires post-patch →
  `verification: not-fixed` (the finding stays `confirmed` — the patch did not work); the
  finding's class isn't SAST-detectable pre-patch at all, or the patch fails to `git apply` →
  `verification: static-only` (stays `confirmed` — real but unverified by this mechanism); and
  a `deps`-class patch that only bumps to a placeholder version string (e.g. `vX.Y.Z`) is
  rejected as `not-fixed` before the re-scan even runs, since an SCA re-scan can't distinguish
  a real fix from text that no longer matches the old version string.
- **The red-team plan is a document, not an action.** `agents/redteam.md` +
  `agents/redteam-adversary.md` + `sec_overlay.redteam` produce `redteam-plan.md`: a
  prioritization table, manual test directives with `$SHELL_VAR` payloads (never literal
  secrets), and runtime-validation gaps — an *operator* runs these against a live system by
  hand. **The harness itself never executes the target.**
- **The opt-in `prove` phase is the one documented exception**, and it still never touches the
  target's own tree. `agents/prove.md` only runs when `scan_options.prove_findings` is true
  (absent by default); every build and run it drives happens out of tree under
  `{{WORKSPACE}}/repro`, with no network egress — the only oracle is in-band and on loopback.
  `prove.py` applies the resulting proofs deterministically and never edits a finding beyond
  what the recorded proof supports.

## Related pages

- [Pipeline](pipeline.md) — the full phase order this audit runs.
- [Agents](agents.md) — the prompts spawned at each phase.
- [Helpers](helpers.md) — `preflight.py`, `verify.py`, and the other deterministic modules
  invoked above.
- [Developing the skill](developing-the-skill.md) — the test suite, including the two env-only
  failures in more detail.
