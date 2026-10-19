---
type: how-to-guide
title: Running a sec-overlay Audit
description: The deterministic smoke-scan command, the audit CLI's deterministic phase driver, the diff-scoped review track, CI integration via the composite GitHub Action, preflight tool checks, environment prerequisites, and how the harness upholds its never-execute-the-target invariant.
tags: [sec-overlay, running-audit, preflight, smoke-scan, review, ci]
---

# Running a sec-overlay audit

There are three ways to run this harness: a fast deterministic **smoke scan** with no agents at
all, the **full agentic audit** via the `audit` CLI subcommand and [pipeline](pipeline.md), and a
lighter **diff-scoped review** of one pull request. All three start from
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

## Full agentic audit — the `audit` CLI and the deterministic driver

```bash
cd skills/sec-overlay/helpers
uv run python -m sec_overlay.cli audit --target <T> --workspace <WS>
```

`cli.py`'s `audit` subcommand calls `driver.run_audit`, which walks
`phases.PHASE_TABLE` (see [pipeline](pipeline.md#the-full-phase-order)): every deterministic
phase runs automatically and records its stage; the first agent phase it reaches halts and
prints the exact dispatch instructions (prompt path, substituted `{{TOKEN}}` values) instead of
calling a model itself. The orchestrating agent reads that halt message, spawns the named
subagent with the rendered prompt, persists its return with
`workspace.record_agent_return(ws, "<agent-label>", <text>)` (→ `runs/<agent>.txt`), and re-runs
`audit` to resume from the next phase. Disk state is always the source of truth — the driver
never depends on a subagent's chat summary propagating. If a host hard-blocks a subagent's Write
tool on a `findings`/`report`/`summary`-like path, the `OUTPUT_WRITE_FALLBACK` prompt-constants
block instructs writing via a `python3 shutil.copy` from a temp file instead, so a blocked write
never silently loses a finding. `run.py`'s `fence()` additionally guards every pass against the
audited working tree changing mid-run (a `git status --porcelain` baseline comparison),
raising loudly rather than scanning a tree that moved under it.

## Diff-scoped review (`review`)

```bash
uv run python -m sec_overlay.cli review \
  --base <base-ref> --head <head-ref> --root <path-to-code> \
  --profile security   # or: general
```

A separate, lighter pipeline over one diff — not the full audit above, and with no phase driver:
it is a loop the orchestrating agent runs directly, over one `review-file` subagent per
reviewable file (see [agents — diff-review pipeline](agents.md#diff-review-pipeline--a-separate-lighter-track)).
`--profile security` (the default) reproduces the full gate ladder byte-for-byte; `--profile
general` relaxes two of the five exclusion gates for a general-defect class (null-dereference,
thread-safety, resource-leak, error-swallowing, injection) — a strict superset of the security
profile's output, never a change to it.

The five-step loop: **prepare** (`--prepare`, writes `runs/review_plan.json` and one rendered
`review-file.md` prompt per reviewable file) → **dispatch** (spawn one `review-file` subagent per
file, in waves of three to four, bounded by `--concurrency`) → **prepare reflection**
(`--prepare-reflection`, renders one `review-filter.md` prompt per file with kept findings) →
**dispatch reflection** (spawn `review-filter` subagents the same way) → **consume** (re-run
`review` with no `--prepare*` flag; reads both recorded passes back from disk and runs the full
gate chain: position gate → `apply_profile` → the reflection filter → the receipt gate). Every
review artifact resolves under the same per-repo memory sidecar as `scan`/`audit`
(`<root>/.sec-overlay/<repo-slug>/`), never at `--root` itself; pass the identical
`--workspace`/`--model` values to every invocation of one review, or a resumed run is rejected
(exit 2) rather than silently mixing state. Exit 0 on a `complete` coverage seal, 2 on an invalid
ref/unsafe rule file/model mismatch, 3 when one or more files could not be reviewed.

## CI integration — review mode as a GitHub Action

`plugins/sec-overlay/action.yml` is a composite GitHub Action that packages the `review` command
above for pull-request CI: it runs `sec_overlay.cli review` against the PR's base/head, uploads
`report.sarif` to code scanning if it was produced, and posts findings as a pull-request review
via `sec_overlay.pr_poster` (critical/high findings inline, the rest in the summary). The review
event it posts is `COMMENT`, so it never blocks a merge on its own — an operator or CodeRabbit
decides what to do with the findings. `pr_poster.py` is stdlib Python (no Node dependency),
consistent with the helpers core's no-runtime-dependency rule. This is distinct from, and
runs independently of, this *repository's own* CI gate on sec-overlay's source
(`.github/workflows/sec-overlay-tests.yml`, see
[security automation](../../operations/security-automation.md#sec-overlays-own-ci-gate)) —
`action.yml` is the plugin's shipped capability for a *consumer's* repository, not this repo's
own test gate.

## Preflight — the first gate

```bash
uv run python -m sec_overlay.preflight
```

`helpers/sec_overlay/preflight.py`'s `check_tools()` checks for seven binaries: `semgrep`, `rg`
(ripgrep), `codeql`, `tree-sitter`, `ast-grep`, `osv-scanner`, and `gitleaks`. Three of them —
`tree-sitter`, `osv-scanner`, `gitleaks` (the `_OPTIONAL` set) — are **optional**: a scan
degrades gracefully and logs them as skipped rather than crashing preflight. The other four —
`semgrep`, `rg`, `codeql`, `ast-grep` — are required backends the scan depends on (`rg` backs
route-census and the structural index, so it is no longer merely incidental tooling).
`preflight` also reports which toolchains the opt-in `prove` lane needs
(`sec_overlay.prove.PROVE_TOOLCHAINS`), since that phase only runs when `scan_options.
prove_findings` is set. `preflight` prints the exact install command for anything missing.
**It never installs — the operator runs the printed commands.**

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

A clean checkout is missing one thing a full audit needs:

1. **The semgrep rules submodule.** `rules/semgrep/` is gitignored and must be fetched with
   `git clone --depth 1 https://github.com/semgrep/semgrep-rules rules/semgrep` (the exact
   command `preflight.py`'s remediation prints), not `git submodule update` — it is a plain
   gitignored directory, not a tracked git submodule. Without it, semgrep has no vendored rules
   and `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` fails. This is the
   **only** environmental, expected-to-fail test on a clean checkout — do not "fix" it by
   committing the rules clone.
2. **External tool binaries.** `uv run python -m sec_overlay.preflight` must show semgrep, `rg`,
   codeql (+ language packs), ast-grep, osv-scanner present for a fully-covered run.
3. **The bench corpus now ships committed.** `bench/corpus_seed/*.json` holds only public
   entries (public-app advisories pinned to a commit, dependency-CVE lockfiles, and synthetic
   fixtures under `helpers/fixtures/`) and is **tracked**, not gitignored — so
   `test_bench.py::test_seed_corpus_is_valid`/`test_seed_corpus_has_min_entries` and
   `test_citations.py::test_all_mapped_ids_exist_in_seed` run in CI
   (`.github/workflows/sec-overlay-tests.yml`) and pass on a clean checkout too. The corpus is
   still **dev/bench-only** — a grading oracle, not part of an audit run; never add a confirmed
   vulnerability from private code to the seed. See
   [developing the skill](developing-the-skill.md#the-bench-harness-dev-only-not-part-of-an-audit).

## The do-not-execute-the-target invariant

The harness never runs, builds, or modifies the code it is auditing, with one narrow, opt-in
exception.

- **Static analysis only, except the opt-in `prove` lane.** Every SAST backend (`sast.py`,
  `codeql.py`, `sca.py`, `secrets.py`) parses source or scans dependency manifests; none of them
  execute the target. The one exception is `agents/prove.md` / `sec_overlay.prove` — phase 24 in
  [pipeline](pipeline.md), gated entirely behind `scan_options.prove_findings` (absent/false by
  default, so a normal audit never runs it). All building and running happen out of tree under
  `ws.repro`, never in the target's own working directory; a proof promotes a finding to
  `confirmed` only when the agent drove a real entrypoint and a wrapper-decidable oracle observed
  the effect.
- **Patch verification uses a throwaway copy.** `helpers/sec_overlay/verify.py` copies the
  target, applies the proposed `patch_diff` with `git apply`, re-runs the SAST on **the copy**,
  and compares pre/post presence of the finding's class. The original target is never modified.
  The comparison resolves to one of four outcomes: flagged pre-patch and gone post-patch →
  `status: fixed`, `verification: verified-static` (the only outcome that promotes a finding to
  `fixed`); the patch applies cleanly but the same class of hit still fires post-patch →
  `verification: not-fixed` (the finding stays `confirmed` — the patch did not work); the
  finding's class isn't SAST-detectable pre-patch at all, or the patch fails to `git apply` →
  `verification: static-only` (stays `confirmed` — real but unverified by this mechanism); and
  a `deps`-class patch that only bumps to a placeholder version string is rejected as
  `not-fixed` before the re-scan even runs.
- **The red-team plan is a document, not an action.** `agents/redteam.md` +
  `agents/redteam-adversary.md` + `sec_overlay.redteam` produce `redteam-plan.md`: a
  prioritization table, manual test directives with `$SHELL_VAR` payloads (never literal
  secrets), and runtime-validation gaps — an *operator* runs these against a live system by
  hand.

## Related pages

- [Pipeline](pipeline.md) — the full phase order this audit runs, and the deterministic driver.
- [Agents](agents.md) — the prompts spawned at each phase, including the diff-review pipeline.
- [Helpers](helpers.md) — `preflight.py`, `verify.py`, `driver.py`, and the other deterministic
  modules invoked above.
- [Developing the skill](developing-the-skill.md) — the test suite and the bench harness.
- [Security automation](../../operations/security-automation.md) — this repository's own CI gate
  on sec-overlay's source, distinct from `action.yml`'s consumer-facing CI integration.
