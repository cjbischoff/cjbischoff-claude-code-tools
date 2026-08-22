# Phase 3: Rule Matching & Review Modes - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers per-language rule selection and the two review profiles. A new
glob rule matcher (`rule_glob.py`) resolves each file's rule doc through four
layers with safety caps on rule-file reads. Nine per-language rule docs ship as
LLM prompt payloads. The `review` verb gains `--profile security|general`:
security reproduces the current gate A-E behavior exactly; general surfaces
rule-doc defect classes that gates A/B would drop, with gates C/D/E still
applied. A retract-only, fail-open reflection filter runs per file after
positioning and the hunk gate. The mechanical receipt gate remains the sole
authority on `confirmed`. Requirements: RULE-01..05, REV-01..03. Bundling,
concurrency, resume, and diff-anchored output belong to Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Glob matcher and Python floor
- **D-01:** Keep `requires-python = ">=3.12"`. Ship a small custom `**`-aware
  matcher instead of `PurePath.full_match` (3.13). — **Reversibility:** reversible —
  a later floor bump can swap the matcher for `full_match` behind the same function.
- **D-02:** Byte-mirror OCR `system_rules.go` semantics for brace expansion and
  matching; port OCR test cases where they exist. Divergence from OCR is a defect.
- **D-03:** Document the floor decision in the helpers README and in a comment
  next to `requires-python` in `pyproject.toml`.
- **D-04:** Lower-case both the path and the pattern before matching, so a
  mixed-case user pattern still matches.

### Rule docs and resolution
- **D-05:** Rule docs are LLM prompt payloads, not human documents. Port OCR's
  field-tested checklists keeping their terse imperative prompt format. Do NOT
  apply an STE100 style pass. Adapt only where sec-overlay vocabulary differs
  (status/severity terms). — **Reversibility:** reversible.
- **D-06:** The user `rule.json` schema mirrors OCR exactly (ordered PathRules,
  pattern, rule path, `merge_system_rule`, excludes) so OCR configs port
  unchanged. — **Reversibility:** costly — schema changes break every user
  config at project and global layers.
- **D-07:** Built-in rule docs live at `skills/sec-overlay/rules/rule_docs/` per
  spec §5. The new directory needs its own README per repo governance.
- **D-08:** A rule-file safety violation (symlink escape, disallowed extension,
  over 512 KB) rejects the run with an actionable error naming the path and
  reason. No silent fallback to the next resolution layer — a typo'd rule path
  must never silently review with the wrong checklist.

### General profile mechanics
- **D-09:** Gates A/B relax via a class-allowlist bypass: only findings tagged
  with a rule-doc general-defect class (NPE, thread-safety, resource-leak,
  error-swallowing, injection) skip gates A/B. Everything else still faces A-E.
- **D-10:** REV-01 no-regression proof is a same-fixture dual-run test: one diff
  fixture through both profiles; security output must match pre-phase gate
  behavior exactly; general output is the security superset plus rule-doc
  classes.
- **D-11:** The defect class rides in a new field in the review-mode
  payload/ledger (new modules), never in `models.py`. — **Reversibility:**
  one-way for the frozen contract — `models.py`/`evidence.py` are byte-mirrored
  by the Go port and must not change.
- **D-12:** Default disposition for general-defect findings without a Tier-1
  receipt: static-checkable classes (NPE, error-swallowing, resource leak) ship
  as `unconfirmed`; runtime-dependent classes (thread-safety races) ship as
  `needs-deployment-testing`. Mirrors AUD-03 discipline.

### Reflection filter
- **D-13:** Invocation split: SKILL.md instructs Claude to spawn the filter
  subagent per file (phase-adversary pattern); a new `reflection.py` owns prompt
  payload build, response validation, and retraction application. No CLI or API
  dependency in helper code. — **Reversibility:** reversible.
- **D-14:** Every retraction gets a dropped-findings ledger entry (path, line,
  reason `reflection-retracted`, the filter's analysis text) in both report and
  JSON. Extends Phase 2 D-14 never-silent discipline.
- **D-15:** Fail-open events are logged per file (file, error summary,
  `reflection-skipped` marker) in report and JSON, so a run where reflection
  never worked is distinguishable from one that retracted nothing.
- **D-16:** Protected-subject vetoes (memory safety, concurrency, linkage
  consistency, behavioral/compatibility change, unused parameter) are enforced
  in the prompt AND in code: `reflection.py` mechanically rejects any retraction
  of a protected-class finding. LLM output is never trusted alone.

### Claude's Discretion
- Internal data structures of the custom glob matcher and `reflection.py`.
- Exact ledger/JSON field names for retractions and fail-open markers (within
  the never-silent discipline above).
- CLI flag wiring order (`--rule`, `--exclude`, `--profile`) and how the review
  verb's finding source connects to the gate ladder.
- Fixture strategy for the dual-run regression test.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec (primary)
- `/Users/christopher/Workspace/review_open-code-review/spec_sec-overlay-improvement_20260816_0920.md`
  §1 (two review modes), §4 (rule matcher, resolution, safety,
  merge_system_rule), §5 (rule docs), §6 (reflection filter ordering and
  vetoes) — the authoritative designs this phase implements. Outside the repo;
  if unreachable at planning time, stop and ask.

### Milestone planning
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria 1-5, and the Python
  floor note.
- `.planning/REQUIREMENTS.md` — RULE-01..05, REV-01..03 exact wording.
- `.planning/intel/constraints.md` — stdlib-only invariant, frozen-contract rule.

### Gate definitions
- `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md` —
  EXCLUSION_RULES gates A-E text that the security profile must preserve and
  the general profile selectively bypasses.
- `plugins/sec-overlay/skills/sec-overlay/SKILL.md` (lines ~28-48) — phase
  adversary gate pattern that D-13 mirrors for reflection dispatch.

### Prior phase decisions
- `.planning/phases/02-diff-pipeline-positioning/02-CONTEXT.md` — carried
  forward: exit codes 2/3 as CLI contract (D-06/D-15), drops/declines always
  ledgered never silent (D-13/D-14), injectable runner pattern, OCR-mirroring
  discipline.
- `.planning/phases/01-baseline-health-verification/01-CONTEXT.md` — frozen
  `models.py`/`evidence.py` contract (D-02), Python floor decision explicitly
  deferred to this phase (D-11), uv-run gate commands (D-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sec_overlay/cli.py`: `review` verb tracer path exists (`run_review`, exit
  codes 0/2/3); no finding source wired yet — this phase connects rules,
  profiles, and reflection into it.
- `sec_overlay/phase_gate.py`: `review_position_gate` already lands review-mode
  findings; profile branching composes beside it.
- `sec_overlay/rule_matcher.py`: existing content/regex ASVS pre-filter — spec
  §4.1 explicitly says do NOT reuse it; the new module is `rule_glob.py`.
- `sec_overlay/findings_gate.py` + `evidence.py`: the mechanical receipt gate
  the reflection filter composes under (REV-03).
- `tests/` conventions: pytest with fake-runner doubles; dual-run fixture test
  (D-10) follows this pattern.

### Established Patterns
- Stdlib-only core (ADR-2026-08-04) — custom glob matcher, `json` for rule.json,
  no new dependency.
- Frozen contract: new fields live in new modules' payloads, never `models.py`.
- Phase adversary gates: skill spawns the agent, Python module validates and
  applies verdicts — the reflection filter reuses this shape.

### Integration Points
- `cli.py` gains `--profile`, `--rule`, `--exclude` on the `review` subparser.
- `rule_glob.py` output selects the rule doc injected as `{{system_rule}}` into
  the reviewing agent's prompt.
- Reflection runs per file after `positioning.py` and the hunk gate, before
  `findings_gate.py` (spec §6 ordering).
- `pyproject.toml` `requires-python` gains the floor-decision comment (D-03).

</code_context>

<specifics>
## Specific Ideas

- Mirror OCR (`open-code-review`) wherever the spec cites a Go source:
  `system_rules.go` (matcher semantics, resolution layers, safety,
  merge_system_rule), OCR rule docs (checklist content), REVIEW_FILTER_TASK
  (reflection prompt, in `notes/ocr-cli-config.md` Part 3).
- Rule docs are machine-consumed prompt payloads: terse imperative checklists
  with explicit exclusions, NOT STE100 prose. The file type determines the
  checklist — that determinism is the phase's answer to prompt instability.

</specifics>

<deferred>
## Deferred Ideas

- CLI override for the 5000-line size cap — Phase 4 owns the flag surface
  (carried from Phase 2).

</deferred>

---

*Phase: 03-rule-matching-review-modes*
*Context gathered: 2026-08-17*
