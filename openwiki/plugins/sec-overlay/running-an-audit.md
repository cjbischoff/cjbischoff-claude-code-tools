---
type: how-to-guide
title: Running a sec-overlay Audit
description: The deterministic smoke-scan command versus a full agentic audit, preflight tool checks, environment prerequisites and the two known env-only test failures, and how the harness upholds its never-execute-the-target invariant.
tags: [sec-overlay, running-audit, preflight, smoke-scan]
---

# Running a sec-overlay audit

There are three ways to run this harness, from lightest to heaviest: a fast deterministic
**smoke scan** with no agents at all; a **diff-scoped review** of one pull request (see
[diff-review](diff-review.md)); and the **full agentic audit** described in
[pipeline](pipeline.md), drivable either manually per `SKILL.md` or through the
[`/sec-overlay:audit`](#the-sec-overlayaudit-command) slash command. All start from
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
[prefilter phase](pipeline.md#the-full-phase-order-manual--skillmd-narrative), which runs all
four concurrently. It also never calls `sec_overlay.state.begin_pass`, so it does not pin a SHA
or advance the campaign's `pass_number` — a smoke scan is a one-shot prefilter run, not a pass
in the multi-pass campaign model described in [pipeline](pipeline.md#multi-pass-campaigns). It
is the fast path to see output — **not** a real audit: no agents run, so there is no
investigate gate ladder, no adversarial validation, and no `risk_score`. The bundled
`rules/smoke.yaml` is a minimal ruleset; the vendored semgrep-rules clone (fuller semgrep
coverage — a gitignored shallow clone, not part of the plugin's tracked files) is not part of
the plugin — for a real audit, point `--config` (and the recon agent's `rulesets`) at your own
semgrep ruleset.

## The `/sec-overlay:audit` command

[`plugins/sec-overlay/commands/audit.md`](/plugins/sec-overlay/commands/audit.md) —
`/sec-overlay:audit <repo> [<repo> ...]` — is the packaged entry point for a full audit. With
one repo argument it drives that repo's audit and stops; with two or more it drives each
repo's audit, infers each one's correlation role from its scan profile
(`sec_overlay.run.infer_role`), confirms the inferred roles with the operator, then correlates
them (`sec_overlay.run.synthesize_manifest` + `python -m sec_overlay.correlate`) — see
[cross-repo correlation](cross-repo-correlation.md). Internally it calls
`sec_overlay.run.drive(repo, config=...)`, which walks `sec_overlay.phases.PHASE_TABLE`
automatically for deterministic phases and prints a "NEXT AGENT PHASE" block for each agent
phase; the orchestrator runs that agent, then calls `sec_overlay.run.advance(repo, phase)` to
close it (fence + receipt + `record_stage`) before re-invoking `drive`. See
[pipeline — the driver and PHASE_TABLE](pipeline.md#the-driver-and-phase_table-the-newer-auto-sequencer)
for which phases this automates today.

## Full agentic audit (manual, per `SKILL.md`)

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
`rg` (ripgrep — route census + call-edge search), `codeql`, `tree-sitter`, `ast-grep`,
`osv-scanner`, and `gitleaks`. Three of them — `tree-sitter`, `osv-scanner`, `gitleaks` (the
`_OPTIONAL` set) — are **optional**: a scan degrades gracefully and logs them as skipped
rather than crashing preflight. The other four — `semgrep`, `rg`, `codeql`, `ast-grep` — are
required backends the scan depends on. `preflight` prints the exact install command for
anything missing. **It never installs — the operator runs the printed commands.**

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

A clean checkout is missing one thing a full audit needs, and ships one thing you might
expect to be missing but is not:

1. **The vendored semgrep ruleset is missing by default.** `rules/semgrep/` is a
   **gitignored, shallow-cloned directory, not a git submodule** — there is no `.gitmodules`
   entry. Seed it with `git clone --depth 1 https://github.com/semgrep/semgrep-rules
   rules/semgrep` (the exact command `preflight.py` prints when the directory is missing).
   Without it, semgrep has no rules and
   `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` fails.
   `helpers/rules/absence/` is a separate, **tracked, first-party** rule pack that ships with
   the plugin — never write a first-party rule under `helpers/rules/semgrep/`, since
   `preflight.py` recreates that directory from the clone and deletes anything else there.
2. **External tool binaries.** `uv run python -m sec_overlay.preflight` must show `semgrep`,
   `rg`, `codeql` (+ language packs), and `ast-grep` present (the four required backends).
3. **The bench corpus ships committed, not gitignored.** `bench/corpus_seed/*.json` holds
   only public entries (synthetic fixtures, dep-CVE lockfiles, pinned public-app advisories —
   see [developing the skill](developing-the-skill.md#the-bench-harness-dev-only-not-part-of-an-audit)),
   so `test_bench.py::test_seed_corpus_is_valid`/`test_seed_corpus_has_min_entries` and
   `test_citations.py::test_all_mapped_ids_exist_in_seed` run in CI, not just on a
   developer's own private-corpus checkout.

**The one env-only failure on a clean checkout is environmental, not a code defect** — do not
"fix" it by committing the vendored clone's contents into the repo:
`tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` (excluded
vendored semgrep clone). The skill `CLAUDE.md` §1 states this explicitly. Older wiki/plan
notes referring to a *second* environmental failure from a gitignored bench corpus predate the
corpus becoming committed — see item 3 above.

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

## Related pages

- [Pipeline](pipeline.md) — the full phase order this audit runs.
- [Diff-review](diff-review.md) — the lighter, PR-scoped `sec-overlay review` alternative.
- [Agents](agents.md) — the prompts spawned at each phase.
- [Helpers](helpers.md) — `preflight.py`, `verify.py`, and the other deterministic modules
  invoked above.
- [Developing the skill](developing-the-skill.md) — the test suite, including the env-only
  failure in more detail.
- [Cross-repo correlation](cross-repo-correlation.md) — what the `/sec-overlay:audit` command
  does with two or more repo arguments.
