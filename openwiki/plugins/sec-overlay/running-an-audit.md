---
type: how-to-guide
title: Running a sec-overlay Audit
description: The deterministic smoke-scan command versus a full agentic audit versus the diff-scoped review mode, preflight tool checks, environment prerequisites and the one known env-only test failure, the slash command and GitHub Action surfaces, and how the harness upholds its never-execute-the-target invariant (with its one opt-in exception).
tags: [sec-overlay, running-audit, preflight, smoke-scan]
---

# Running a sec-overlay audit

There are three ways to run this harness against a single repo: a fast deterministic
**smoke scan** with no agents at all, the **full agentic audit** described in
[pipeline](pipeline.md), and a lighter **diff-scoped `review`** over one pull request's changes
(below). All three start from `skills/sec-overlay/helpers/` — inside an installed plugin, that
is `${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/helpers`. Two more surfaces (the slash command and
the GitHub Action, also below) wrap these commands for everyday use.

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
ruleset; the vendored semgrep-rules clone (fuller semgrep coverage, gitignored — see
[environment prerequisites](#environment-prerequisites-for-a-full-run)) is not part of the
plugin — for a real audit, point `--config` (and the recon agent's `rulesets`) at your own
semgrep ruleset.

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

`helpers/sec_overlay/preflight.py`'s `check_tools()` checks for six binaries: `semgrep`,
`codeql`, `tree-sitter`, `ast-grep`, `osv-scanner`, and `gitleaks`. Three of them —
`tree-sitter`, `osv-scanner`, `gitleaks` (the `_OPTIONAL` set) — are **optional**: a scan
degrades gracefully and logs them as skipped rather than crashing preflight. The other three —
`semgrep`, `codeql`, `ast-grep` — are required backends the scan depends on. `preflight`
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
stated identically in `SKILL.md` and the skill's own [`CLAUDE.md`](/plugins/sec-overlay/skills/sec-overlay/CLAUDE.md) §2.

## Environment prerequisites for a full run

A clean checkout is missing one thing a full audit needs — the vendored semgrep ruleset:

1. **The vendored semgrep ruleset.** `helpers/rules/semgrep/` is a **gitignored, shallow-cloned
   directory** (`git clone --depth 1 https://github.com/semgrep/semgrep-rules
   helpers/rules/semgrep`, the exact command `preflight.py` prints when it's missing) —
   **not** a git submodule; there is no `.gitmodules` entry. Without it, semgrep has no rules
   and `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` fails.
   `helpers/rules/absence/` is a separate, tracked, first-party rule pack that ships with the
   plugin and is unaffected.
2. **External tool binaries.** `uv run python -m sec_overlay.preflight` must show semgrep,
   codeql (+ language packs), ast-grep, osv-scanner present.

**The bench corpus ships committed**, not gitignored: `bench/corpus_seed/*.json` holds only
public entries (public-app advisories pinned to a commit, dep-CVE lockfiles, and synthetic
fixtures under `helpers/fixtures/` — never a confirmed vulnerability from private code), so
`test_bench.py::test_seed_corpus_is_valid`, `test_seed_corpus_has_min_entries`, and
`test_citations.py::test_all_mapped_ids_exist_in_seed` run clean on a fresh checkout and in CI
(`.github/workflows/sec-overlay-tests.yml` runs a detection-regression gate off this same
corpus). It is still **dev/bench only** — see
[developing the skill](developing-the-skill.md#the-bench-harness-dev-only-not-part-of-an-audit).

**The one env-only failure on a clean checkout is environmental, not a code defect** — do not
"fix" it by committing the semgrep-rules clone: `tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`.
The skill `CLAUDE.md` §1 states this explicitly.

## Diff-scoped review (`review`)

A separate, lighter track from the full audit above — reviews one diff (`--base`/`--head`),
not a whole repository:

```bash
cd skills/sec-overlay/helpers
uv run python -m sec_overlay.cli review \
  --base <base-ref> --head <head-ref> --root <path-to-code> \
  --profile security   # or: general
```

`--profile security` (default) reproduces the full audit's gate ladder byte-for-byte; `general`
relaxes two gates for five specific defect classes (`GENERAL_PROFILE_EXCLUSION_RULES`, a strict
superset of `security`'s output). The command has no phase driver: it is a three/four-step loop
the main agent runs directly — **prepare** (writes `runs/review_plan.json` + one prompt per
changed file from `agents/review-file.md`), **dispatch** (spawn a `review-file` subagent per
file, in waves of three to four, persisting each return to disk), **prepare-reflection**
(renders one `agents/review-filter.md` retract-only fact-check per file with kept findings),
**dispatch reflection**, then **consume** (reads both back, runs the position gate → profile
gate → reflection filter → tool-receipt gate, writes `report.md` + `artifacts/review_result.json`).
Output resolves under the same per-repo sidecar as `scan`/`audit`
(`<root>/.sec-overlay/<repo-slug>/`), never at `--root` itself. Exit 0 on a `complete` coverage
seal, 2 on an invalid ref/unsafe rule file/model-or-profile mismatch on resume, 3 when one or
more files could not be reviewed. See
[agents — the diff-review track's own prompts](agents.md#the-diff-review-tracks-own-prompts-not-part-of-the-table-above)
and [helpers — diff-scoped review modules](helpers.md#module-map-grouped-by-job).

## The slash command and the GitHub Action

Two more surfaces wrap the CLI commands above:

- **`/sec-overlay:audit <repo> [<repo> ...]`** (`plugins/sec-overlay/commands/audit.md`) — a
  thin routing document, no executable logic of its own. One repo: drives the single-repo audit
  loop via `sec_overlay.run.drive`/`advance` and stops. Two or more repos: drives each repo's
  audit, infers each repo's role from its `kb/scan-profile.json`
  (`sec_overlay.run.infer_role`), confirms with the operator, then synthesizes a manifest
  (`sec_overlay.run.synthesize_manifest`) and runs `python -m sec_overlay.correlate` — see
  [cross-repo correlation](cross-repo-correlation.md).
- **`action.yml`** (plugin root) — a composite GitHub Action for pull requests: runs `review`
  in a temp workspace, uploads the SARIF via `github/codeql-action/upload-sarif`, then posts
  findings as a PR review through `sec_overlay.pr_poster` (stdlib `urllib` only — no runtime
  dependency added). The review event is always `COMMENT`, so this action never blocks a merge
  on its own, matching this repository's own comment-only CodeRabbit posture (see
  [code review](../../governance/code-review.md)).

## The do-not-execute-the-target invariant

The harness never runs, builds, or modifies the code it is auditing — with one named, opt-in
exception. This holds at every phase that touches code:

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
  hand. **The harness itself never executes the target through this path.**
- **The one exception: the opt-in `prove` phase.** `agents/prove.md` + `sec_overlay.prove.py`
  may build and run target-derived code, but only when `scan_options.prove_findings` is
  explicitly `true` (default off, so a normal audit never triggers it), and only out-of-tree
  under `ws.repro` — never inside the target's own working copy. See
  [pipeline — the prove lane](pipeline.md#the-prove-lane-an-opt-in-exception-to-never-execute)
  and [`docs/decisions/2026-08-31-prove-lane-execution.md`](/docs/decisions/2026-08-31-prove-lane-execution.md)
  for the conditions and trade-offs.

## Related pages

- [Pipeline](pipeline.md) — the full phase order this audit runs.
- [Agents](agents.md) — the prompts spawned at each phase.
- [Helpers](helpers.md) — `preflight.py`, `verify.py`, and the other deterministic modules
  invoked above.
- [Developing the skill](developing-the-skill.md) — the test suite, including the one env-only
  failure in more detail.
