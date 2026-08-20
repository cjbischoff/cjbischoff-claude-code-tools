# Phase 5: End-to-End Verification (Audit & Review) - Research

**Researched:** 2026-08-20
**Domain:** Verification of an existing, already-shipped tool (sec-overlay plugin) against a real external target repo — not new feature development
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Audit target**
- **D-01:** The audit target is the local work repo `/Users/christopher/Documents/Development/_hy/mando` (React Router + Cloudflare Functions TypeScript app). — **Reversibility:** reversible — a different target only changes run inputs, not tool code.
- **D-02:** Pin the audit to mando's `main` HEAD at run start. Record the SHA in the receipts (`80e2abc` at discussion time; re-resolve at run time). Do not audit the live working tree.
- **D-03:** Audit the full repo with the tool's default excludes (node_modules, build outputs, lockfiles). Use the full AUD-05 coverage denominator. Do not narrow scope to app/ and functions/.

**Review diff**
- **D-04:** The review run uses a real historical diff from mando — the same target as the audit. No seeded or synthetic diff this phase.
- **D-05:** The planner selects the concrete diff by criteria, not by name. Criteria: a merged PR or commit range that touches roughly 5–30 allowlisted files (TS/TSX), mixes app/ and functions/ code, and stays within the default per-file size caps. The executor resolves the exact `base..head` SHA range at run time and records it.
- **D-06:** Run both profiles (`security`, then `general`) on the identical SHA range. This evidences the Phase 3 D-10 profile-superset contract on real code.

**Evidence capture**
- **D-07:** Full run artifacts (reports, findings, coverage manifests, ledgers) stay in mando's `.sec-overlay` sidecar. This marketplace repo commits sanitized receipts only: commands, exit codes, seal states, headline counts, gate verdicts, and SHAs. No mando file paths, code snippets, or finding bodies enter this repo. — **Reversibility:** one-way for history — committed mando internals cannot be removed from git history later.
- **D-08:** The phase verifier reads the sidecar live at mando to check the six success criteria. Committed receipts cite what to check and where. No artifact copies.
- **D-09:** Retain the sidecar artifacts untouched until the v5.0 milestone ships (through Phase 6 and the milestone audit). Record the sidecar path in the receipts.

**Defect disposition**
- **D-10:** Phase 5 fixes run-blockers only: defects that stop a run from completing or sealing (crashes, hangs, gate false-halts). Fixes follow full governance (branch, Conventional Commit, version bump, tests). All other defects (finding quality, noisy output, scoring oddities) go to the defect ledger for Phase 6.
- **D-11:** The defect ledger is `05-DEFECTS.md` in this phase directory. Each entry records: defect, severity, repro command, disposition (`fixed-here` or `deferred`). The D-07 sanitization rule applies to ledger entries.
- **D-12:** A success-criterion failure on real output (for example, a Tier-2-only finding reaches `confirmed`) is a ledger entry, not a run-blocker. The phase verification reports `gaps_found` honestly. Closure comes through a gap plan or Phase 6. Do not re-run until green to hide the defect.

### Claude's Discretion
- Concrete diff selection within the D-05 criteria.
- Receipt document structure, provided it follows the Phase 1 evidence format (exact command, exit code, decisive tail lines, version block — 01-CONTEXT D-05..D-07).

### Deferred Ideas (OUT OF SCOPE)
- Handing audit findings to the mando team (triage, issue filing) — outside this milestone; the runs here verify the tool, not mando.
- Seeded-defect detection benchmark diff — considered for AUD-06, not selected; could become a fixture-based regression suite in a later milestone.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUD-01 | A full `/sec-overlay:audit` run completes end to end on a real target repo, with per-phase receipts written and the working-tree fence intact [VERIFIED: .planning/REQUIREMENTS.md:114-116] | `run.py`'s `drive()`/`advance()` fence+receipt closure and `phases.py`'s 22-entry `PHASE_TABLE` (see Architecture Patterns) show exactly how "per-phase receipt" and "fence intact" are produced and can be checked in the sidecar. |
| AUD-02 | Every finding with status `confirmed` cites a mechanical tool receipt; Tier-2-only or syntactic-match evidence never reaches `confirmed` [VERIFIED: .planning/REQUIREMENTS.md:117-118] | `evidence.py`'s `_MECHANICAL`/`TIER1_RECEIPTS`/`TIER2_RECEIPTS`/`confirms_alone()` and `findings_gate.py`'s hard `validate_findings()` check give the exact receipt-tier gate the run report must satisfy. |
| AUD-03 | Runtime-dependent findings land in `needs-deployment-testing` with a real risk score, visible in report headline counts [VERIFIED: .planning/REQUIREMENTS.md:120-121] | `calibrate.py`'s `_SCOREABLE = {FindingStatus.CONFIRMED, FindingStatus.NEEDS_DEPLOYMENT_TESTING}` proves `needs-deployment-testing` findings are scored, not skipped. |
| AUD-04 | Architecture and threat-model artifacts pass the deterministic gates (Mermaid caps, derivation headers, STE lint) and score with CVSS v4.0 only [VERIFIED: .planning/REQUIREMENTS.md:123-124] | `diagram_gate.py`'s `CAPS`/`SEQ_CAPS`/provenance-header check, `ste_lint.py`'s sentence/paragraph limits, and `cvss.py`'s hard rejection of any non-`CVSS:4.0` vector give the exact pass/fail conditions. |
| AUD-05 | The audit report states its coverage denominator; every attack-surface class without a finding has a logged coverage-ledger entry [VERIFIED: .planning/REQUIREMENTS.md:126-127] | `coverage_ledger.py`'s `build_coverage_ledger()`/`validate_coverage_ledger()` machine-enforce this: `completeness == "complete"` is impossible while any surface is `needs_follow_up`. |
| AUD-06 | A full `review` run (both profiles) completes end to end on a real diff, with the coverage manifest sealed and positioning-confirmed line numbers [VERIFIED: .planning/REQUIREMENTS.md:129-130] | `review_coverage.py`'s `CoverageManifest.seal()` (raises on any non-`done` entry) and `review_findings.py`'s `apply_profile()` (the profile-superset contract) ground the dual-profile run's completion criteria. |
</phase_requirements>

## Summary

Phase 5 does not build anything new — it proves, on a real external repo, that the sec-overlay plugin's two shipped pipelines (`/sec-overlay:audit` and `cli.py review`) behave exactly as their own code says they do. Every one of the six success criteria (AUD-01 through AUD-06) already has a concrete, deterministic enforcement point in the shipped code, verified this session by reading the actual module: `run.py` (fence + receipt), `phases.py` (the real 22-phase table), `evidence.py`/`findings_gate.py` (Tier-1-only confirmation gate), `calibrate.py` (risk scoring including `needs-deployment-testing`), `diagram_gate.py`/`ste_lint.py`/`cvss.py` (architecture/threat-model gates and CVSS v4.0-only scoring), `coverage_ledger.py` (audit coverage denominator), and `review_coverage.py`/`review_findings.py` (review coverage seal and profile superset). The planner's job is to sequence two real runs against mando and produce sanitized receipts — not to design new mechanisms.

Two facts materially affect planning. First, no commit in mando's visible git history satisfies D-05's literal diff-selection criteria (5-30 allowlisted files, mixing `app/` and `functions/`) within the size caps — see Open Questions. Second, this machine already has every external tool the audit pipeline needs except the vendored semgrep rules content, which has a verified one-line fix.

**Primary recommendation:** Drive the audit through `/sec-overlay:audit`'s existing `run.py` entry point against mando pinned at `main` HEAD (per D-02); drive the review through `cli.py review --profile security` then `--profile general` against one resolved `base..head` range (per D-05/D-06); commit only sanitized receipts to this repo (per D-07); log every gap in `05-DEFECTS.md`, fixing only true run-blockers (per D-10..D-12).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Working-tree fence + per-phase receipts (AUD-01) | sec-overlay driver (`run.py`/`driver.py`) | mando target repo (read-only) | The fence/receipt logic lives entirely in the plugin's Python helpers; mando is only the object being fenced. |
| Tier-1 tool-receipt confirmation gate (AUD-02) | sec-overlay deterministic pipeline (`evidence.py`, `findings_gate.py`) | External scanners (semgrep, codeql, ast-grep, osv-scanner) | The gate is enforced in-process; the scanners are the actual receipt producers it trusts. |
| Risk scoring incl. runtime-dependent findings (AUD-03) | sec-overlay deterministic pipeline (`calibrate.py`) | — | Pure deterministic post-processing of findings already on disk; no external dependency. |
| Architecture/threat-model gates + CVSS v4.0 (AUD-04) | sec-overlay deterministic pipeline (`diagram_gate.py`, `ste_lint.py`, `cvss.py`) | Agent-authored artifacts (`architecture/`, `threat-model/`) | Gates are deterministic checks over agent-produced Markdown/Mermaid; the agents are outside this phase's build scope (already shipped). |
| Coverage-completeness ledger (AUD-05) | sec-overlay deterministic pipeline (`coverage_ledger.py`) | Recon output (`scan-profile.json` attack_surface) | The ledger is derived math over recon's own declared surface list; recon is upstream, not built here. |
| Diff-scoped dual-profile review + coverage seal (AUD-06) | sec-overlay review pipeline (`cli.py review`, `review_coverage.py`, `review_findings.py`) | mando target repo (diff source) | Review logic and manifest sealing are entirely in-process; mando supplies only the git history being diffed. |
| Evidence sanitization / receipt authoring for this phase | This repo's phase deliverable (`05-DEFECTS.md`, receipt docs) | — | New work product for this phase — the only thing actually "built" in Phase 5. |

## Standard Stack

No new libraries. This phase runs already-shipped, stdlib-only tooling (`plugins/sec-overlay/CLAUDE.md`: *"The core is stdlib-only by design — no runtime dependencies in pyproject.toml"* [CITED: plugins/sec-overlay/CLAUDE.md]) against external CLI scanners already installed on this machine (see Environment Availability). REL-03's zero-new-runtime-dependency invariant (referenced in STATE.md decision log) is unaffected by this phase.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| N/A | — | — | Phase adds no dependency; it exercises the existing sec-overlay Python package and external scanner CLIs already on PATH. |

### Supporting
N/A — no new packages.

### Alternatives Considered
N/A — nothing to choose between; the pipelines under test are fixed by prior milestone phases.

**Installation:** None required for code. See Environment Availability for the one external-tool-content gap (vendored semgrep rules).

## Package Legitimacy Audit

**Not applicable.** This phase installs zero external packages. No `npm install`/`pip install`/`cargo add` occurs. The Package Legitimacy Gate is skipped by design (no packages to check).

## Architecture Patterns

### System Architecture Diagram

```
mando repo (external target, read-only)
   |
   |  git rev-parse HEAD  (pin SHA, D-02)
   v
run.py: drive(target, config, ...)
   |-- _load_baseline()  -- capture `git status --porcelain` once at pass start
   |-- write_env() -> run.env
   |-- build AuditContext(ws, target, config, sha)
   v
driver.py: run_audit(ctx, table=PHASE_TABLE, on_complete=on_complete)
   |
   +--> loop: next_actionable_phase(table, state)
          |
          +-- deterministic phase --> run_deterministic_phase()
          |        |-- checks missing_inputs()
          |        |-- runs DETERMINISTIC_ACTIONS[name](ctx)
          |        |-- checks outputs_present()
          |        |-- on_complete(name)  == fence() + receipt()   [AUD-01]
          |        |-- record_stage(ws, name)
          |
          +-- agent phase --> render_dispatch() (prints prompt+substitutions, returns)
                   orchestrator runs the model externally, writes declared outputs
                   next loop pass: auto-advances (if output-only) or main agent calls advance()

on_complete closure (defined inside drive(), run.py):
   fence(target, baseline, runner=runner)     -- raises WorkingTreeFenceError if tree changed  [AUD-01 fence]
   receipt(ws, phase_name, counts={...})       -- writes kb/receipts/<phase>.json               [AUD-01 receipt]

findings pipeline (subset of PHASE_TABLE, deterministic phases):
   prefilter -> investigate(agent) -> findings-gate -> dedupe -> critic(agent) -> judge(agent)
   -> validate(agent) -> trace(agent) -> factcheck -> calibrate -> patch(agent) -> verify
   -> demote-noise -> report -> selfscore -> artifact-gate -> artifact-review(agent)
        |                                        |
        v                                        v
   evidence.py: confirms_alone()          calibrate.py: calibrate_score()
   (Tier-1-only confirms)   [AUD-02]       (scores CONFIRMED + NEEDS_DEPLOYMENT_TESTING) [AUD-03]

architecture/threat-model side-branch (own gates, run before prefilter in real sequence):
   architecture(agent) -> arch-gate (diagram_gate.py + ste_lint.py)          [AUD-04]
   threat_model(agent) -> tm-gate  (diagram_gate.py + ste_lint.py + dup check) [AUD-04]
   CVSS scoring anywhere a finding/threat gets a vector -> cvss.py (CVSS:4.0-only) [AUD-04]

coverage-ledger side-branch (reads recon's declared surface, all findings):
   coverage_ledger.build_coverage_ledger(ws)  -> kb/coverage-ledger.json      [AUD-05]
   validate_coverage_ledger()  -- "complete" forbidden while any surface is needs_follow_up

--- separately, the review pipeline (own CLI entry, not part of PHASE_TABLE) ---

mando repo (same target)
   |
   |  base..head SHA range resolved at run time (D-05)
   v
cli.py review --base <sha> --head <sha> --profile security   (first run)
cli.py review --base <sha> --head <sha> --profile general    (second run, identical range, D-06)
   |
   +-- review_coverage.CoverageManifest: add() -> start() -> finish()/fail() per file
   |        seal()  -- raises CoverageTransitionError unless every entry is "done"  [AUD-06 seal]
   +-- review_findings.apply_profile(findings, profile)
            security: drops every gate A-E marked finding
            general:  keeps gate A/B only if in GENERAL_DEFECT_CLASSES allowlist, else drops;
                      gates C/D/E drop under both profiles                          [AUD-06 superset]
```

### Recommended Run Structure (this phase's own deliverables, not new code)
```
.planning/phases/05-end-to-end-verification-audit-review/
├── 05-CONTEXT.md          # already exists — locked decisions
├── 05-DISCUSSION-LOG.md   # already exists — audit trail only
├── 05-RESEARCH.md         # this file
├── 05-PLAN.md             # planner's output
├── 05-DEFECTS.md          # D-11 defect ledger (fixed-here / deferred)
└── 05-*-receipt.md        # sanitized command+exit-code+tail receipts (D-07, Phase 1 format)
```

### Pattern 1: Fence-then-receipt on every deterministic phase (AUD-01)
**What:** `on_complete(phase_name)` runs `fence()` before `receipt()` for every deterministic phase and every auto-advancing agent phase.
**When to use:** Already wired into `drive()`; the executor does not re-implement this — it just runs `/sec-overlay:audit` and reads the resulting `kb/receipts/<phase>.json` files in mando's sidecar.
**Example (mechanism, not a call the planner writes):**
```python
# Source: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/run.py (read in full this session)
# drive()'s inline on_complete closure — exact ordering is fence, then receipt.
def on_complete(phase_name: str) -> None:
    fence(target, baseline, runner=runner)
    receipt(ws, phase_name, counts={"findings": len(read_findings(ws))})
```

### Pattern 2: Tier-1-only confirmation gate (AUD-02)
**What:** `findings_gate.validate_findings(ws)` hard-fails any finding whose status is `confirmed`/`fixed` but whose `evidence_sources` contain no Tier-1 receipt.
**When to use:** Runs automatically as the `findings-gate` deterministic phase (`driver.py:175-181`, `_act_findings_gate`) — the planner verifies AUD-02 by reading `report.md`/`report.sarif`'s confirmed findings and cross-checking each cites a `semgrep:`/`codeql:`/`sca:`/`secrets:`-prefixed source (Tier-1 per `evidence.py`'s `TIER1_RECEIPTS = frozenset({"codeql", "semgrep", "sca", "secrets"})`).
**Example:**
```python
# Source: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py (read in full this session)
TIER1_RECEIPTS = frozenset({"codeql", "semgrep", "sca", "secrets"})
TIER2_RECEIPTS = frozenset({"ripgrep", "structural-index", "ast-grep", "tree-sitter"})

def confirms_alone(sources) -> bool:
    return any(receipt_tier(s) == 1 for s in sources)
```

### Pattern 3: CVSS v4.0-only hard rejection (AUD-04)
**What:** `cvss.py`'s `_parse()` raises `ValueError` on any `CVSS:3*` vector and on any vector that is not `CVSS:4.0/...`.
**When to use:** Verifies automatically — any threat-model or finding CVSS vector this run produces must already be `CVSS:4.0`; the planner's verification step is to grep the produced artifacts for `CVSS:` strings and confirm none start with `CVSS:3`.
**Example:**
```python
# Source: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cvss.py (read in full this session)
def _parse(vector: str) -> dict[str, str]:
    if vector.startswith("CVSS:3"):
        raise ValueError(f"CVSS 3.x vector is no longer supported; re-derive as CVSS:4.0 ({vector})")
    if not vector.startswith("CVSS:4.0/"):
        raise ValueError(f"not a CVSS 4.0 vector: {vector}")
    ...
```

### Anti-Patterns to Avoid
- **Citing `repo_memory.py`'s `PHASES` tuple as the audit's phase list.** That tuple is a 12-item legacy list used only by `RepoMemory.run_status()` for `MEMORY.md` human status text. The real order the driver walks is `phases.py`'s 22-entry `PHASE_TABLE` (`recon, architecture, arch-gate, threat_model, tm-gate, prefilter, investigate, findings-gate, dedupe, critic, judge, validate, trace, factcheck, calibrate, patch, verify, demote-noise, report, selfscore, artifact-gate, artifact-review` [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py — full 22-entry `PHASE_TABLE`, read in full this session]). A receipt document that cites the short list will not match what actually gets a `kb/receipts/<phase>.json` file.
- **Re-scanning or re-running to "fix" a bad result instead of logging it.** D-12 explicitly forbids re-running until green to hide a gap — a Tier-2-only finding that reaches `confirmed` in the real run is a `05-DEFECTS.md` entry, not a reason to tweak inputs and try again.
- **Committing mando file paths, snippets, or finding bodies to this repo.** D-07 is one-way (git history cannot un-leak this later) — every receipt must be re-read against the "sanitized: commands, exit codes, seal states, counts, gate verdicts, SHAs only" rule before staging.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting a working-tree mutation during the audit | A new git-diff snapshot/compare script | `run.py`'s existing `fence()` (baseline captured once via `_load_baseline`, compared via `git status --porcelain`) | Already implemented, already wired into every phase's `on_complete`; a parallel implementation risks disagreeing with the shipped one and would not be what the actual `/sec-overlay:audit` run uses. |
| Deciding whether a finding may say `confirmed` | A new "is this evidence good enough" heuristic | `evidence.py`'s `confirms_alone()` / `findings_gate.validate_findings()` | This is exactly AUD-02's enforcement mechanism; it already runs as a gated phase (`findings-gate`) and hard-halts the run on violation. |
| Scoring a threat/finding severity | Manual CVSS arithmetic or an LLM-estimated score | `cvss.py`'s `cvss40_base()` (ports FIRST's official CVSS v4.0 MacroVector/interpolation algorithm, BSD-2-Clause) | AUD-04 requires CVSS v4.0 only; the module already hard-rejects anything else and is a verified port of the official calculator, not ad-hoc math. |
| Checking coverage completeness | A manual checklist of attack-surface classes | `coverage_ledger.build_coverage_ledger()` / `validate_coverage_ledger()` | The ledger's `completeness` field is machine-derived from recon's own `attack_surface` list crossed with findings; it is the literal AUD-05 denominator, not a document a human writes by hand. |
| Tracking per-file review progress across a resumed run | A custom JSON state file for the review pass | `review_coverage.py`'s `CoverageManifest` (states, allowed transitions, identity pinning) | Already implements the exact state machine (`pending → in_review → {done, failed}`) AUD-06 needs, including the resume-identity check (`check_resume_identity`) this phase's dual-profile run depends on. |

**Key insight:** Every mechanism the six success criteria describe is already implemented and gated in the shipped pipeline. Phase 5's job is exclusively to *run* it against a real target and *read* its own receipts — building a parallel verification mechanism would duplicate logic that already exists and is more likely to disagree with the real run than confirm it.

## Common Pitfalls

### Pitfall 1: Citing the wrong phase list
**What goes wrong:** A receipt or plan cites `repo_memory.py`'s short `PHASES` tuple (12 entries) as "the phases the audit ran," and a receipt then appears to be "missing" phases like `arch-gate`, `tm-gate`, `judge`, `trace`, `factcheck`, `demote-noise`, `selfscore`, `artifact-gate`, `artifact-review` that were, in fact, run.
**Why it happens:** Two similarly-named phase lists exist in the codebase for different purposes — `phases.py`'s `PHASE_TABLE` (driver-authoritative) and `repo_memory.py`'s `PHASES` (human status-line display only).
**How to avoid:** Always resolve "what phases ran" against `phases.py`'s `PHASE_TABLE` and the `kb/receipts/*.json` files actually present in the sidecar, never against `repo_memory.py`.
**Warning signs:** A receipt document listing exactly 12 phases when the sidecar's `kb/receipts/` directory has more files than that.

### Pitfall 2: Trusting the plugin CLAUDE.md's submodule claim
**What goes wrong:** Following `plugins/sec-overlay/CLAUDE.md`'s instruction — *"Semgrep rules are a git submodule (`helpers/rules/semgrep/`). Clone with `--recurse-submodules`"* [VERIFIED: plugins/sec-overlay/CLAUDE.md — quoted verbatim] — produces no rules content, because this repo has no `.gitmodules` file and `git submodule status` returns nothing (both verified live this session).
**Why it happens:** Doc drift — the doc describes a submodule setup that was never actually wired for this repo (or was removed).
**How to avoid:** Use the plain-clone remediation the preflight check itself prints: `git clone --depth 1 https://github.com/semgrep/semgrep-rules skills/sec-overlay/helpers/rules/semgrep`. This is the verified-working fix on this machine.
**Warning signs:** `uv run python -m sec_overlay.preflight` reporting `[MISSING] vendored semgrep rules` despite having run `git submodule update --init --recursive`.

### Pitfall 3: No natural diff in mando satisfies D-05's literal criteria
**What goes wrong:** Searching mando's history for "a merged PR touching 5-30 allowlisted files, mixing `app/` and `functions/`" turns up nothing, because mando's `functions/` directory contains exactly one 359-byte file (`functions/[[path]].ts`, a Cloudflare Pages catch-all route) that has only ever been touched by 5 commits total, all of which are either far over the 30-file cap (~111 or 43 files) or 14+ months stale (see Open Questions for the full list).
**Why it happens:** mando's actual architecture concentrates almost all routing logic in `app/`, with `functions/` reduced to a one-line passthrough — the "mixing" criterion assumes a repo shape mando does not have.
**How to avoid:** Flag this to the plan/executor explicitly rather than force-fitting an over-cap commit; the planner has discretion (per Claude's Discretion in CONTEXT.md) to relax the mixing criterion, accept a documented deviation, or select an `app/`-only diff and log the criterion gap per D-12.
**Warning signs:** Any diff-selection commit range with a file count far outside 5-30, or one whose only `functions/` touch is 14+ months old.

### Pitfall 4: Assuming `factcheck` will produce a receipt
**What goes wrong:** Expecting `kb/receipts/factcheck.json` to always exist and treating its absence as a run failure.
**Why it happens:** `factcheck` is deliberately a soft no-op when `kb/verdicts.json` is absent — `driver.py`'s `_act_factcheck` docstring states: *"Until that agent exists, the file is absent and this phase no-ops silently — the input is deliberately not a hard gate (see phases.py), so a missing verdict artifact never halts the run."* [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py:200-214, quoted verbatim]
**How to avoid:** Do not flag a no-op `factcheck` phase as a defect; confirm via `record_stage`/state.json that the phase is marked done, not via an output artifact.
**Warning signs:** A defect-ledger entry for "factcheck produced no output" when no fact-check agent exists yet in this milestone.

## Code Examples

### Driving the audit (SKILL.md's `/sec-overlay:audit` entry point)
The full audit is driven by the `/sec-overlay:audit` slash command, which runs `skills/sec-overlay/CLAUDE.md`'s documented phase order end to end — this is not a single raw CLI call; agent phases dispatch a subagent per the printed `render_dispatch()` block and the main orchestrator calls `advance()` once that phase's declared outputs exist:
```
# Source: plugins/sec-overlay/skills/sec-overlay/CLAUDE.md §2 "How to run an audit" (read in full this session, verbatim section header/table)
0  Preflight        python -m sec_overlay.preflight
1  Begin pass       sec_overlay.state.begin_pass(ws, sha)
...
2  Recon            agents/recon.md (sonnet) -> kb/scan-profile.json   # -> PHASE GATE
3  Architecture     agents/architecture.md (sonnet) -> architecture/ tree
3.5 Arch gate       python -m sec_overlay.diagram_gate + ste_lint
4  Threat model     agents/threat-model.md (sonnet) -> threat-model/ tree
4.5 TM gate         diagram gate + ste_lint + duplication check
5  Prefilter        sec_overlay.prefilter.run_prefilter(ws, target, profile)
...
14 Report           python -m sec_overlay.report --workspace <WS>
14.5 Artifact gate  python -m sec_overlay.artifact_gate --workspace <WS>
```
For a quick deterministic-only smoke check (not a substitute for the real audit — it skips every agent phase):
```bash
# Source: plugins/sec-overlay/skills/sec-overlay/CLAUDE.md §2 "Quick deterministic scan (no agents)"
cd skills/sec-overlay/helpers
uv run python -m sec_overlay.cli scan \
  --target <T> --workspace <WS> --config rules/smoke.yaml \
  --sha "$(git -C <T> rev-parse HEAD)"
```

### Driving the review (dual profile, D-06)
```bash
# Source: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:610-651 (read in full this session; flags/defaults verbatim)
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -m sec_overlay.cli review \
  --base <resolved-base-sha> --head <resolved-head-sha> \
  --root /Users/christopher/Documents/Development/_hy/mando \
  --profile security
# then, identical range (D-06):
uv run python -m sec_overlay.cli review \
  --base <resolved-base-sha> --head <resolved-head-sha> \
  --root /Users/christopher/Documents/Development/_hy/mando \
  --profile general
```
Verified defaults (`cli.py:62-64`, read this session): `DEFAULT_CONCURRENCY = 8`, `DEFAULT_TIMEOUT_SECONDS = 600`, `DEFAULT_MAX_GIT_PROCS = 16`. `--head` defaults to `HEAD`; `--root` defaults to `.`; `--profile` is one of `{"security", "general"}`, default `security` (`cli.py:611-614`). `--model` is "an opaque model identity string recorded on the coverage manifest; a resumed run with a different `--model` is rejected (exit 2)" (`cli.py:646-651`, quoted verbatim) — the same `--model` value must be used if the review pass is resumed.

## State of the Art

Not applicable in the usual sense — this phase adopts no new external technology. The one relevant "state of the art" fact is that CVSS v4.0 is the pinned scoring standard for this harness (ruling R2, per STATE.md's decision log: *"CVSS v4.0 pinned harness-wide (ruling R2); Mermaid caps hard-enforced"* [VERIFIED: .planning/STATE.md:96, quoted verbatim]), and `cvss.py` enforces it in code, not by convention.

**Deprecated/outdated:**
- CVSS 3.x vectors: explicitly rejected by `cvss.py`'s `_parse()` — any `CVSS:3*` vector raises `ValueError` rather than being silently accepted or auto-converted.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `SHA` mentioned in D-02 (`80e2abc` "at discussion time") will differ from the SHA actually resolved at run time, since `main` moves. | User Constraints / Code Examples | Low — D-02 itself instructs re-resolving at run time; this is expected, not a defect. |
| A2 | mando's git history has not changed since the investigation performed earlier this session (git log against `functions/` returning 5 commits total). | Open Questions | Low-medium — if mando's `main` has advanced with a new commit touching both `app/` and `functions/` within the cap since this research, a compliant diff may now exist; the executor should re-run the same `git log --oneline -- functions/` check at plan/execution time before accepting this research's negative finding as final. |
| A3 | The `report.md`/`report.sarif` produced by a real audit run will expose enough per-finding `evidence_sources` detail to mechanically verify AUD-02 (Tier-1-only confirmation) without opening raw `findings/*.json` files. | Architecture Patterns / Code Examples | Low — even if the summary report abbreviates evidence, the underlying `findings/<ID>.json` files (per the workspace-artifacts list in `skills/sec-overlay/CLAUDE.md` §4) always carry `evidence_sources` in full; the verifier can fall back to those. |

**If this table is empty:** N/A — three low-risk assumptions logged above; every structural/code claim in this document is `[VERIFIED: file:line]` from a direct read this session.

## Open Questions

1. **No commit in mando's history satisfies D-05's literal diff-selection criteria.**
   - What we know: `git log --oneline -400 -- functions/` in `/Users/christopher/Documents/Development/_hy/mando` returns exactly 5 commits across the repo's entire visible history: `5d6b72e` (2026-06-04 "Feat/upgrade to rrv7 v2 (#736)", ~111 files), `243bb20` (2025-06-04, revert of same, ~111 files), `d473a5f` (2025-06-04 "feat: upgrade to react router v7 (#720)", ~111 files), `f9665fd` (2025-03-03 "chore(future flags): single fetch and lazy route discovery (#602)", 43 files), `1ec10ff` (ancient, "feat: init remix and cloudflare (#32)", 34 files). mando's `functions/` directory holds exactly one file, `functions/[[path]].ts` (a Cloudflare Pages catch-all). Every one of the 5 commits either exceeds D-05's 30-file cap (three commits at ~111 files, two at 43 and 34 files) — none falls in the 5-30 range.
   - What's unclear: Whether D-05's "mixes app/ and functions/" criterion was written assuming a repo shape mando does not have (mando's `functions/` is a single 359-byte passthrough, not a meaningfully separate code area), and whether the planner should (a) relax the mixing criterion and accept an `app/`-only diff in the 5-30 range, (b) accept one of the over-cap commits as a documented deviation, or (c) treat this as a D-12 "success-criterion failure on real output" ledger entry outright.
   - Recommendation: Re-run the same `git log --oneline -- functions/` check at plan/execution time (mando's `main` may have advanced since this research). If still empty, select an `app/`-only diff in the 5-30 file range (satisfies file-count and file-type criteria; fails only the "mixes" sub-criterion) and log the mixing-criterion deviation explicitly in `05-DEFECTS.md`/the receipt per D-12, rather than silently loosening or silently exceeding the cap.

2. **Exact `--config`/rules path for the audit run.**
   - What we know: `cli.py`'s `audit` subcommand requires `--config` (`cli.py:604-608`, read this session: `audit.add_argument("--config", required=True)`); the full `/sec-overlay:audit` slash-command path likely resolves this internally, but the exact default ruleset path used by the full audit flow (vs. the `scan --config rules/smoke.yaml` smoke path) was not directly confirmed by reading `commands/audit.md` this session.
   - What's unclear: Whether the planner needs to pass an explicit `--config` value or whether `/sec-overlay:audit` resolves one automatically.
   - Recommendation: Read `plugins/sec-overlay/commands/audit.md` at plan time (listed in 05-CONTEXT.md's canonical_refs) to confirm the exact invocation before writing the audit-run task.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| semgrep | Prefilter, verify, review dataflow | ✓ | confirmed via `command -v semgrep` | — |
| codeql (+ query packs: actions, cpp, csharp, go, java, javascript, python, ruby, rust, swift) | Prefilter dataflow | ✓ | confirmed via `command -v codeql` + preflight pack list | — |
| ast-grep | Structural matching | ✓ | confirmed via `command -v ast-grep` | — |
| osv-scanner | SCA (Tier-1 `sca` receipts) | ✓ | confirmed via `~/.ghost/bin/osv-scanner` on PATH | — |
| tree-sitter | Structural index | ✓ | reported `[OK]` by preflight | — |
| gitleaks | Secrets scanning | ✓ | reported `[OK]` by preflight | — |
| uv | Running the Python helper package | ✓ | `uv 0.11.32 (Homebrew 2026-07-23 x86_64-apple-darwin)` | — |
| git | Fence, diff resolution, SHA pinning | ✓ | `git version 2.55.0` | — |
| Python | Runtime for `sec_overlay` package | ✓ | `Python 3.13.14` | — |
| Vendored semgrep rules (`helpers/rules/semgrep/`) | Full ruleset for prefilter/verify | ✗ | — | `git clone --depth 1 https://github.com/semgrep/semgrep-rules skills/sec-overlay/helpers/rules/semgrep` (verified command; plugin CLAUDE.md's "git submodule" claim does not match this repo's actual config — no `.gitmodules`, `git submodule status` returns nothing) |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Vendored semgrep rules content — one `git clone` away; not a submodule despite the plugin doc's claim.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (sec-overlay helper package); this phase's own "tests" are the two real pipeline runs themselves |
| Config file | `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` (dev deps: pytest, ruff, ty only, per plugin CLAUDE.md) |
| Quick run command | `uv run python -m sec_overlay.preflight` (environment check before either real run) |
| Full suite command | Not the unit suite — the phase's actual verification is: complete `/sec-overlay:audit` run against mando + complete `cli.py review` run (both profiles) against mando, each read back against its six success criteria |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUD-01 | Full audit completes; fence intact; per-phase receipts written | integration (real run) | `/sec-overlay:audit` against mando, then inspect `kb/receipts/*.json` in mando's `.sec-overlay/<slug>/` sidecar | N/A — receipts are produced by the run, not pre-existing |
| AUD-02 | Every `confirmed` finding cites a Tier-1 receipt | integration (real run + grep) | Inspect `findings/*.json`/`report.sarif` for `confirmed` entries; cross-check `evidence_sources` against `TIER1_RECEIPTS` | ✅ — enforced live by `findings-gate` phase during the run itself |
| AUD-03 | `needs-deployment-testing` findings carry a real risk score in headline counts | integration (real run + report read) | Inspect `report.md` headline counts and per-finding `risk_score` for any `needs-deployment-testing` entries | ✅ — enforced live by `calibrate` phase |
| AUD-04 | Architecture/threat-model pass gates; CVSS v4.0 only | integration (real run; gate is hard-halting) | `kb/gates/arch-gate.json`, `kb/gates/tm-gate.json` — `{"passed": true}` required to proceed past those phases | ✅ — enforced live by `arch-gate`/`tm-gate` deterministic phases |
| AUD-05 | Coverage denominator stated; every unfound surface has a ledger entry | integration (real run + ledger read) | Inspect `kb/coverage-ledger.json`'s `completeness` field and per-surface `disposition` | ✅ — `validate_coverage_ledger()` machine-rejects a false "complete" |
| AUD-06 | Both review profiles complete; coverage manifest sealed; positions confirmed | integration (two real runs) | Inspect the review sidecar's `coverage_manifest.json` `seal` field (must be `"complete"` or documented `"partial"`) for each profile run | ✅ — `CoverageManifest.seal()` raises rather than allowing a false claim |

### Sampling Rate
- **Per task commit:** `uv run python -m sec_overlay.preflight` (confirm environment still intact before/after any run-blocker fix).
- **Per wave merge:** Full audit run + full dual-profile review run against mando.
- **Phase gate:** All six success criteria read back from the real sidecar artifacts (D-08) before `/gsd-verify-work`; any failure is a `05-DEFECTS.md` entry per D-12, not a blocked gate — this phase's own gate is "ran end to end and reported honestly," not "zero findings."

### Wave 0 Gaps
None — existing test infrastructure (pytest suite plus the shipped deterministic gates) covers all phase requirements; the phase's own "test" is the real run, which is the deliverable itself.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase touches no auth surface — it runs a security tool against a target, it does not add auth code. |
| V3 Session Management | no | Not applicable. |
| V4 Access Control | no | Not applicable. |
| V5 Input Validation | yes (indirectly) | The tooling under test (`findings_gate.py`'s schema validation, `cvss.py`'s vector-format rejection) already enforces input validation on its own artifacts; this phase does not add new input-handling code. |
| V6 Cryptography | no | Not applicable — no new crypto code this phase. |

### Known Threat Patterns for this phase
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Sensitive data disclosure (mando's proprietary code/paths leaking into this public-facing marketplace repo) | Information Disclosure | D-07's sanitized-receipts-only rule, enforced by review before every commit in this phase: commands, exit codes, seal states, headline counts, gate verdicts, and SHAs only — no mando file paths, code snippets, or finding bodies. |
| Committing a run-blocker fix without governance | Tampering (of the shipped tool's trust) | D-10 requires any run-blocker fix to follow full governance (branch, Conventional Commit, version bump, tests) — same as any other plugin change. |
| Silently re-running to hide a real gap | Repudiation (of the harness's own honesty guarantee) | D-12 forbids re-running until green; a real success-criterion failure is logged in `05-DEFECTS.md` and reported as `gaps_found`, never hidden. |

## Sources

### Primary (HIGH confidence — read in full this session, verbatim quotes used where cited)
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/run.py` — fence, receipt, `drive()`, `advance()`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py` — `PHASE_TABLE` walk, `run_deterministic_phase()`, `run_audit()`, `DETERMINISTIC_ACTIONS`, `_act_factcheck` docstring
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py` — authoritative 22-entry `PHASE_TABLE`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py` — `_MECHANICAL`, `TIER1_RECEIPTS`, `TIER2_RECEIPTS`, `confirms_alone()`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py` — `validate_findings()` Tier-1-only enforcement
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/coverage_ledger.py` — `build_coverage_ledger()`, `validate_coverage_ledger()`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/calibrate.py` — `_SCOREABLE`, `calibrate_score()`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py` — `CoverageManifest`, `seal()`, `check_resume_identity()`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diagram_gate.py` — `CAPS`, `SEQ_CAPS`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/ste_lint.py` — sentence/paragraph limits
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cvss.py` — CVSS v4.0-only `_parse()`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/file_select.py:1-45` — `DEFAULT_MAX_DIFF_LINES = 5000`, `ALLOWED_EXTENSIONS`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py` — `GENERAL_DEFECT_CLASSES`, `apply_profile()`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:604-673` — `audit`/`review` subcommand flags and defaults
- `plugins/sec-overlay/CLAUDE.md` — maintainer manual, submodule claim (found inaccurate against live `git submodule status`)
- `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md` — full audit phase-order table, workspace artifact layout, signal-over-noise architecture
- `.planning/REQUIREMENTS.md:114-131` — AUD-01 through AUD-06 verbatim
- `.planning/STATE.md` — decision log (CVSS v4.0 ruling, coverage manifest shape, etc.)
- `.planning/phases/05-end-to-end-verification-audit-review/05-CONTEXT.md` — locked decisions D-01..D-12
- `.planning/phases/05-end-to-end-verification-audit-review/05-DISCUSSION-LOG.md` — confirms no additional decisions beyond CONTEXT.md
- `.planning/config.json` — confirms `workflow.nyquist_validation` key absent (Validation Architecture section included)
- Live shell: `uv run python -m sec_overlay.preflight`, `command -v`/version checks for semgrep/codeql/ast-grep/osv-scanner/uv/git, `git submodule status`, `cat .gitmodules` (not found)
- Live shell against `/Users/christopher/Documents/Development/_hy/mando`: `git log --oneline -400 -- functions/`, `git show --stat` on each of the 5 returned commits

### Secondary (MEDIUM confidence)
- None used — every claim in this document is either `[VERIFIED: file:line/live command]` or explicitly logged in the Assumptions Log above.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency decision to make; confirmed via `plugins/sec-overlay/CLAUDE.md`'s explicit stdlib-only statement.
- Architecture: HIGH — every mechanism cited (fence/receipt, Tier-1 gate, CVSS v4.0, coverage ledger, review manifest seal) was read directly from source this session, with line numbers and verbatim quotes.
- Pitfalls: HIGH for the three code-grounded pitfalls (phase-list confusion, submodule doc drift, factcheck no-op); MEDIUM for the mando-diff-selection pitfall since it depends on mando's git history not changing before plan/execution time (flagged as Assumption A2).

**Research date:** 2026-08-20
**Valid until:** 2026-09-19 (30 days — internal tooling is stable; the one time-sensitive fact, mando's git history for D-05 diff selection, should be re-checked at plan/execution time regardless of this window per Assumption A2).
