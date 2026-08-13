---
type: how-to-guide
title: Running a sec-overlay Audit
description: The deterministic smoke-scan command versus a full agentic audit, preflight tool checks, environment prerequisites and the two known env-only test failures, and how the harness upholds its never-execute-the-target invariant.
tags: [sec-overlay, running-audit, preflight, smoke-scan]
---

# Running a sec-overlay audit

There are two ways to run this harness: a fast deterministic **smoke scan** with no agents at
all, and the **full agentic audit** described in [pipeline](pipeline.md). Both start from
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
[prefilter phase](pipeline.md#the-full-phase-order), which runs all four concurrently. It also
never calls `sec_overlay.state.begin_pass`, so it does not pin a SHA or advance the campaign's
`pass_number` — a smoke scan is a one-shot prefilter run, not a pass in the multi-pass campaign
model described in [pipeline](pipeline.md#multi-pass-campaigns). It is the fast path to see
output — **not** a real audit: no agents run, so there is no investigate gate ladder, no
adversarial validation, and no `risk_score`. The bundled `rules/smoke.yaml` is a minimal
ruleset; the semgrep-rules submodule (fuller semgrep coverage) is not part of the plugin — for
a real audit, point `--config` (and the recon agent's `rulesets`) at your own semgrep ruleset.

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
stated identically in `SKILL.md` and the skill's own [`CLAUDE.md`](/plugins/sec-overlay/skills/sec-overlay/CLAUDE.md) §3.

## Environment prerequisites for a full run

A clean checkout is missing three things a full audit needs:

1. **The semgrep rules submodule.** `rules/semgrep/` must be checked out:
   `git submodule update --init --recursive`. Without it, semgrep has no rules and
   `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` fails.
2. **External tool binaries.** `uv run python -m sec_overlay.preflight` must show semgrep,
   codeql (+ language packs), ast-grep, osv-scanner present.
3. **The bench corpus is local-only.** `bench/corpus_seed/*.json` is gitignored (it contains
   confirmed vulnerabilities from private code). Its absence fails
   `test_bench.py::test_seed_corpus_is_valid` and
   `test_citations.py::test_all_mapped_ids_exist_in_seed` — both dev/bench tests, not part of an
   audit. See [developing the skill](developing-the-skill.md#the-bench-harness-dev-only-not-part-of-an-audit)
   to seed it locally.

**The two env-only failures on a clean checkout are environmental, not code defects** — do not
"fix" them by committing the submodule contents or fabricating seed data:
`tests/test_bench.py::test_seed_corpus_is_valid` (gitignored bench corpus) and
`tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` (excluded semgrep
submodule). The skill `CLAUDE.md` §2 states this explicitly.

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
- [Agents](agents.md) — the prompts spawned at each phase.
- [Helpers](helpers.md) — `preflight.py`, `verify.py`, and the other deterministic modules
  invoked above.
- [Developing the skill](developing-the-skill.md) — the test suite, including the two env-only
  failures in more detail.
