# Phase 3: Rule Matching & Review Modes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 03-rule-matching-review-modes
**Areas discussed:** Python floor vs custom matcher, Rule doc authoring, General profile mechanics, Reflection filter integration

---

## Python floor vs custom matcher

| Option | Description | Selected |
|--------|-------------|----------|
| Custom matcher, keep 3.12 | Small stdlib `**`-aware matcher; no floor change; roadmap already leans this way | ✓ |
| Raise floor to 3.13 | Use `PurePath.full_match`; bumps requires-python for all installers | |
| full_match with 3.12 fallback | Two code paths for one behavior; divergence risk | |

**User's choice:** Custom matcher, keep 3.12.

| Option | Description | Selected |
|--------|-------------|----------|
| Byte-mirror OCR semantics | Port expandBraces + match logic exactly; OCR test cases; divergence = defect | ✓ |
| OCR-inspired, own edge behavior | Same features, own edge-case choices | |

**User's choice:** Byte-mirror OCR semantics.

| Option | Description | Selected |
|--------|-------------|----------|
| README + pyproject comment | Floor stated in helpers README plus comment next to requires-python | ✓ |
| README only | Single location; pyproject readers miss rationale | |
| Docstring in rule_glob.py only | Colocated with code; installers never see it | |

**User's choice:** README + pyproject comment.

| Option | Description | Selected |
|--------|-------------|----------|
| Lower-case both sides | Matcher lower-cases path and pattern; forgiving to mixed-case user patterns | ✓ |
| Path only, patterns as-written | Mixed-case user pattern silently never matches | |

**User's choice:** Lower-case both sides.

---

## Rule doc authoring

The user first clarified that the rule docs are machine-consumed: "STE100 is for
human readable reports, machine read documents should be an optimized format for
machine." The original "adapt to STE100" option was withdrawn; the question was
reformulated for prompt-payload format.

| Option | Description | Selected |
|--------|-------------|----------|
| Port OCR, keep prompt format | Copy OCR field-tested checklists in their terse imperative prompt-payload shape; no STE100 pass; adapt only vocabulary differences | ✓ |
| Port OCR verbatim | Byte-copy; OCR vocabulary may clash with sec-overlay finding vocabulary | |
| Author fresh, machine-optimized | New checklists from spec §5; loses field-tested content | |

**User's choice:** Port OCR, keep prompt format.

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror OCR schema | Same rule.json fields; OCR configs port unchanged | ✓ |
| Own schema, OCR-inspired | Cleaner naming; breaks config portability | |

**User's choice:** Mirror OCR schema.

| Option | Description | Selected |
|--------|-------------|----------|
| rules/rule_docs/ per spec | New directory exactly as spec §5 states; needs folder README per governance | ✓ |
| references/rule_docs/ | Reuses references/ tree; departs from spec path | |

**User's choice:** rules/rule_docs/ per spec.

| Option | Description | Selected |
|--------|-------------|----------|
| Reject file, error, no fallback | Unsafe rule file exits with actionable error naming path and reason | ✓ |
| Warn, fall back to next layer | Run proceeds; a typo'd rule path silently reviews with wrong checklist | |

**User's choice:** Reject file, error, no fallback.

---

## General profile mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Class allowlist bypass | Only rule-doc general-defect classes skip gates A/B; all else faces A-E | ✓ |
| Gates A/B off entirely in general | Simpler; weakens security half of general mode | |
| Rewrite A/B as softer variants | Two gate texts to maintain; drift risk | |

**User's choice:** Class allowlist bypass.

| Option | Description | Selected |
|--------|-------------|----------|
| Same-fixture dual-run test | One diff fixture through both profiles; security output must match pre-phase behavior | ✓ |
| Unit tests on gate branch only | No end-to-end proof the security path is untouched | |

**User's choice:** Same-fixture dual-run test.

| Option | Description | Selected |
|--------|-------------|----------|
| New field outside frozen models | Defect class rides in review-mode payload/ledger; models.py untouched | ✓ |
| Encode in existing category field | Overloads a field existing consumers parse | |

**User's choice:** New field outside frozen models.

| Option | Description | Selected |
|--------|-------------|----------|
| Static-checkable=unconfirmed, runtime=NDT | NPE/error-swallowing/resource-leak default unconfirmed; thread-safety races default needs-deployment-testing | ✓ |
| All unconfirmed | Loses AUD-03 nuance for races | |
| All needs-deployment-testing | Mislabels statically-provable NPEs | |

**User's choice:** Static-checkable=unconfirmed, runtime=NDT.

---

## Reflection filter integration

| Option | Description | Selected |
|--------|-------------|----------|
| Skill dispatches agent, module validates | reflection.py owns payload build, validation, retraction; SKILL.md spawns the subagent (phase-adversary pattern) | ✓ |
| Module shells out to claude CLI | Adds CLI availability/auth dependency inside helper code | |

**User's choice:** Skill dispatches agent, module validates.

| Option | Description | Selected |
|--------|-------------|----------|
| Ledger entry per retraction | Path, line, reason, analysis text in report + JSON | ✓ |
| Count only in report | User cannot audit which findings the LLM killed | |

**User's choice:** Ledger entry per retraction.

| Option | Description | Selected |
|--------|-------------|----------|
| Logged per file in report + JSON | Fail-open records file, error summary, reflection-skipped marker | ✓ |
| Silent fail-open | A run with no working reflection looks like one that retracted nothing | |

**User's choice:** Logged per file in report + JSON.

| Option | Description | Selected |
|--------|-------------|----------|
| Both prompt and code | Veto list in prompt AND reflection.py mechanically rejects protected-class retractions | ✓ |
| Prompt only | A hallucinated retraction of a protected finding goes through unchecked | |

**User's choice:** Both prompt and code.

---

## Claude's Discretion

- Internal data structures of the custom glob matcher and reflection.py
- Ledger/JSON field names for retractions and fail-open markers
- CLI flag wiring order and finding-source connection to the gate ladder
- Fixture strategy for the dual-run regression test

## Deferred Ideas

- CLI override for the 5000-line size cap — Phase 4 (carried from Phase 2)
