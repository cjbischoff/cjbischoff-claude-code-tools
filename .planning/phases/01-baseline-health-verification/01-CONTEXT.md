# Phase 1: Baseline Health Verification - Context

**Gathered:** 2026-08-16
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase proves the delivered marketplace and plugin baseline is healthy before any
new module lands. It runs three gate families and makes them green: plugin validation
(VAL-01), sec-overlay quality gates pytest/ruff/ty (VAL-02), and prek hooks repo-wide
(VAL-03). It builds no new capability.

</domain>

<decisions>
## Implementation Decisions

### Failure Policy
- **D-01:** When a gate fails, fix the defect in this phase. The phase completes only
  when all gates pass.
- **D-02:** Fixes must not touch `models.py` or `evidence.py` (frozen JSON contract,
  byte-mirrored by a Go port). If a fix requires a change to a frozen file, stop and
  escalate to the user. — **Reversibility:** one-way — a frozen-contract edit breaks
  the published JSON contract that the Go port mirrors byte for byte.
- **D-03:** A failing test may be changed when the test asserts stale or wrong
  behavior; production code changes when the test asserts intended behavior. Record
  the rationale for each such call in the fix commit message.
- **D-04:** Version bumps follow normal governance: each fix commit that touches a
  sec-overlay shipping file bumps the plugin patch version. No batching exception.

### Evidence Format
- **D-05:** Gate evidence lives in `01-VERIFICATION.md` only. No separate report
  artifact.
- **D-06:** Evidence detail per gate: the exact command, the exit code, and the
  decisive tail lines of output (for example pytest's pass count, ruff's "All checks
  passed").
- **D-07:** `01-VERIFICATION.md` includes a version block that records the versions of
  ruff, ty, pytest, python, and the claude CLI at run time.
- **D-08:** If fixes were needed, `01-VERIFICATION.md` includes a fix ledger table:
  gate, failure, fix summary, commit SHA.

### Tool Pinning
- **D-09:** Run gates with the tool versions installed today. Do not add version pins
  this phase. The version block (D-07) dates the baseline; later phases re-pin only if
  drift causes a failure.
- **D-10:** Run pytest through uv: `uv run pytest` from
  `plugins/sec-overlay/skills/sec-overlay/helpers/`, so the environment resolves from
  that directory's `pyproject.toml`.
- **D-11:** Record the interpreter version but do not declare a `requires-python`
  floor. The floor decision belongs to Phase 3 (glob matcher design; 3.13 gives
  `PurePath.full_match`).

### Gate Scope
- **D-12:** prek runs as `prek run --all-files` across the whole repo, matching the
  VAL-03 wording "passes across the repo".
- **D-13:** ruff and ty run against the helpers package only:
  `plugins/sec-overlay/skills/sec-overlay/helpers/`. Other repo python (for example
  `scripts/`) is out of scope for VAL-02.
- **D-14:** "Zero warnings" means zero unaddressed warnings. Existing justified
  inline ignores (`noqa`, `type: ignore`) count as clean; any new ignore requires a
  justification comment.
- **D-15:** Plugin validation runs twice: `claude plugin validate .` at the repo root
  (marketplace manifest) and inside `plugins/sec-overlay/` (the plugin). Both must
  exit clean.

### Claude's Discretion
- Order of gate execution, and how to structure fix commits within governance rules.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone planning
- `.planning/ROADMAP.md` — Phase 1 goal, VAL-01/02/03 success criteria
- `.planning/REQUIREMENTS.md` — VAL requirement wording and traceability
- `.planning/intel/SYNTHESIS.md` — entry point to the 50-doc delivered-baseline intel

### Milestone spec
- `/Users/christopher/Workspace/review_open-code-review/spec_sec-overlay-improvement_20260816_0920.md`
  — v5.0 milestone spec source (later phases; read for frozen-contract boundaries)

### Governance
- `CLAUDE.md` (repo root) — branch/commit governance, version-bump rules, changelog
  routing that every fix commit must follow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml`: existing project
  config; `uv run` resolves the test environment from it
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/`: existing pytest suite
  (many test modules present)
- `.pre-commit-config.yaml` + prek-generated `.git/hooks/pre-commit`: hooks already
  installed; VAL-03 verifies rather than installs

### Established Patterns
- Governance hooks enforce README/CHANGELOG routing and explicit staging; fix commits
  must satisfy them, not bypass them
- Receipt discipline: claims in VERIFICATION.md quote command output, never assert

### Integration Points
- Phase 2 builds the diff pipeline on top of this verified helpers package; a green
  baseline is its precondition

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Baseline Health Verification*
*Context gathered: 2026-08-16*
