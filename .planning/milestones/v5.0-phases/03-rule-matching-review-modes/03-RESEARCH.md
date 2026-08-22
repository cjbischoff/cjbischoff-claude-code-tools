# Phase 3: Rule Matching & Review Modes - Research

**Researched:** 2026-08-18
**Domain:** Path-glob rule resolution, per-language LLM prompt checklists, dual review-profile gating, retract-only reflection filter
**Confidence:** HIGH

## Summary

Phase 3 has one external spec dependency (the OCR Go source, fully available locally) and
zero new runtime dependencies. The work is mechanical porting plus composition: byte-mirror
`system_rules.go`'s brace-expansion/`**`-matching/resolution-layer semantics into a new
stdlib-only `rule_glob.py`; port 9 OCR rule docs as terse LLM prompt payloads; add
`--profile security|general` to the existing `review_position_gate` pipeline via a
class-allowlist bypass of gates A/B; and build a `reflection.py` module that mirrors the
existing phase-adversary dispatch shape (skill spawns subagent, module validates + applies
verdicts) but is retract-only and fail-open.

The two hazards found in this session are both resolution-order and vocabulary hazards, not
technology hazards: (1) rule-matching resolution is per-path with layer fallthrough, while
`--exclude`/`FileFilter` resolution is whole-layer, first-non-empty-wins with NO fallthrough —
conflating these two under one phrase breaks RULE-02; (2) the `"unconfirmed"` disposition
named in REV-03/D-12 does not exist as a literal value anywhere in the frozen contract
(`models.py`), `evidence.py`, or `prompt-constants.md`'s `EVIDENCE_VOCABULARY` — it must be a
new review-mode-only field per D-11, not a `FindingStatus` member, and this needs explicit
confirmation before the planner locks a field name.

**Primary recommendation:** Treat this phase as a disciplined 1:1 port of OCR's Go semantics
into Python plus a straightforward extension of the existing `review_position_gate` /
phase-adversary machinery — do not redesign either; deviation from OCR is itself a defect per
D-02.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Rule doc resolution (`rule_glob.py`) | CLI / Backend (Python helper) | — | Pure path-matching logic invoked by `cli.py` before prompt assembly; no I/O beyond the resolved rule file |
| Rule-file safety (symlink/ext/size) | CLI / Backend | — | Defense-in-depth read boundary around the resolution above; same module |
| Rule doc content (9 per-language `.md`) | Prompt payload (data, not code) | — | Consumed as `{{system_rule}}` template injection into the reviewing agent's prompt — not rendered to a human |
| `--profile security|general` gating | Backend (gate ladder) | — | `phase_gate.py`/new profile module sits between finding production and `findings_gate.py`; a backend-tier decision, not a CLI concern beyond flag parsing |
| Reflection filter dispatch | Orchestration (SKILL.md) + Backend (`reflection.py`) | — | Mirrors the existing phase-adversary split: skill/agent layer spawns the LLM subagent per file; the Python module owns prompt build, response validation, and mechanical veto enforcement |
| Retraction/fail-open ledger | Backend (`reflection.py` → `report.py`/`review_ledger.json`) | — | Extends the existing `write_review_ledger` artifact, itself backend/report-tier |

## Package Legitimacy Audit

**No new packages.** ADR-2026-08-04 pins a stdlib-only core; `pyproject.toml` confirms
`dependencies = []` [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml] and
REL-03 mandates this stay empty across all new modules. `rule_glob.py`, `reflection.py`, and
the profile-gating logic are pure-Python/stdlib (`json`, `pathlib`, `re`, `fnmatch` as needed).
The Package Legitimacy Gate is not applicable — nothing to check against a registry.

**Packages removed due to [SLOP] verdict:** none — no packages were proposed.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
review CLI invocation (--base --head --profile security|general --rule PATH --exclude GLOB)
        |
        v
run_review() [cli.py, existing]
        |
        +--> resolve_ref_sha(base/head)  -- existing, unchanged
        +--> changed_file_records() / partition()  -- existing DIFF-03 pipeline, unchanged
        |
        v
rule_glob.py  (NEW)
        |  For each reviewable file path (lower-cased):
        |    1. Resolve rule LAYER: --rule flag > .sec-overlay/rule.json (project)
        |       > ~/.sec-overlay/rule.json (global) > built-in rule_docs/
        |       (first layer that has a PathRules match for THIS path wins;
        |        a layer with no match for this path falls through to the next layer)
        |    2. Within the winning layer: walk ordered PathRules, brace-expand each
        |       pattern, **-aware match against the lower-cased path; first match wins,
        |       else fall back to the layer's default rule doc.
        |    3. Safety-check the resolved rule file: resolve symlinks, must stay under
        |       repo root, extension in {.md,.txt,.markdown}, size <= 512 KB.
        |       Violation -> reject the run with an actionable error (no silent fallback).
        |    4. If merge_system_rule: true, concatenate built-in + user rule text under
        |       fixed headers instead of replacing.
        v
{{system_rule}} injected into the per-file review agent prompt (rule_docs/*.md content)
        |
        v
[existing] positioning.py resolve_position()  -->  diffhunks.py hunk gate
        |
        v
reflection.py  (NEW) -- per file, AFTER positioning + hunk gate, BEFORE findings_gate.py
        |  SKILL.md spawns one reflection subagent per file (phase-adversary shape).
        |  reflection.py builds the prompt payload, validates the structured response,
        |  and APPLIES retractions:
        |    - retract-only: can only remove/downgrade a candidate finding, never confirm
        |    - protected-subject vetoes (memory safety, concurrency, linkage consistency,
        |      behavioral/compat change, unused parameter) mechanically re-checked in code,
        |      never trusted from LLM output alone
        |    - fail-open: any LLM/parse error -> finding passes through unfiltered,
        |      logged as a `reflection-skipped` marker (never silently dropped or blocked)
        |  Every retraction -> dropped-findings ledger entry (path, line,
        |    reason="reflection-retracted", filter's analysis text)
        v
review_position_gate() [phase_gate.py, existing]  -- unchanged authority over outside-diff drops
        |
        v
PROFILE BRANCH (NEW, composes beside/after review_position_gate):
        |  security profile: gates A-E enforced exactly as today (EXCLUSION_RULES verbatim)
        |  general profile:  gates A/B bypassed ONLY for findings tagged with a rule-doc
        |    general-defect class (NPE, thread-safety, resource-leak, error-swallowing,
        |    injection) via a class-allowlist; gates C/D/E always enforced in both profiles
        v
findings_gate.py (existing, UNCHANGED authority)
        |  Mechanical Tier-1 receipt (codeql/semgrep/sca/secrets) is the ONLY path to
        |  `confirmed`/`fixed`. General-defect findings without a Tier-1 receipt:
        |    - static-checkable classes (NPE, error-swallowing, resource-leak) -> ship as
        |      new review-mode "unconfirmed" field (NOT a FindingStatus member -- see
        |      Open Questions; frozen contract cannot gain enum values)
        |    - runtime-dependent classes (thread-safety races) -> needs-deployment-testing
        v
report.py write_report()  [existing, extend]
        |  dropped-findings section (already exists, D-14/POS-03 pattern)
        |  position-review section (already exists, D-13/POS-02 pattern)
        |  NEW: reflection retraction entries + reflection-skipped entries in the same
        |  never-silent style, written into review_ledger.json alongside position_reviews
        |  and dropped
```

### Recommended Project Structure
```
plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/
├── rule_glob.py          # NEW — RULE-01..04: path matcher, layer resolution, safety caps
├── reflection.py         # NEW — REV-02: prompt build, response validation, veto enforcement
├── phase_gate.py         # EXISTING — extend for profile branching (gates A-E vs A-relaxed)
├── findings_gate.py      # EXISTING — UNCHANGED, remains sole confirmed/fixed authority
├── cli.py                # EXISTING — add --profile/--rule/--exclude to `review` subparser
├── report.py             # EXISTING — extend write_review_ledger for reflection entries
└── ...
plugins/sec-overlay/skills/sec-overlay/rules/
└── rule_docs/            # NEW dir per D-07 (spec §5): go.md, java.md, python.md, php.md,
                           # rust.md, ts_js_tsx_jsx.md, kotlin.md, swift.md, default.md
                           # + its own README.md (repo governance: new folder needs README)
```

### Pattern 1: Per-path layer fallthrough (rule MATCHING resolution) — RULE-01/RULE-02
**What:** For rule-doc selection, each of the four layers (custom/project/global/built-in) is
tried in order; a layer whose ordered `PathRules` contain no pattern matching the CURRENT path
is skipped and the next layer is tried. This is NOT "first non-empty layer wins" — a layer can
be non-empty (have rules) yet still not match this particular path, and control still falls
through.
**When to use:** `rule_glob.py`'s core resolution loop for RULE-01/RULE-02.
**Source:** `[VERIFIED: /Users/christopher/tools/open-code-review/internal/config/rules/system_rules.go]`
— read directly this session; `composedResolver` walks layers in order and only stops at the
first layer that yields an actual pattern match for the given path, falling through otherwise.
**Example (Python, port of the Go shape):**
```python
# rule_glob.py — NOT verbatim OCR (Go), this is the Python shape to port to; illustrative only
def resolve_rule_doc(path: str, layers: list[RuleLayer]) -> ResolvedRule:
    lowered = path.lower()
    for layer in layers:  # custom, project, global, built-in — in this order
        for rule in layer.path_rules:  # ordered within the layer
            if glob_match(lowered, expand_braces(rule.pattern.lower())):
                return ResolvedRule(rule.rule_path, layer.merge_system_rule)
        # no PathRules entry matched THIS path in this layer -> fall through
    return layers[-1].default_rule  # built-in default, always present
```

### Pattern 2: Whole-layer selection (exclude/FileFilter resolution) — RULE-02 `--exclude`
**What:** For `--exclude` / `FileFilter`, resolution picks the FIRST layer with ANY non-empty
`Include`/`Exclude` list and uses that layer's list ENTIRELY — no per-path fallthrough to a
later layer once a non-empty layer is chosen. `--exclude` on the CLI appends to whichever
layer's list was selected.
**When to use:** Implementing the `--exclude` flag's interaction with layered config in
`rule_glob.py` or a sibling filter module.
**Source:** `[VERIFIED: /Users/christopher/tools/open-code-review/internal/config/rules/system_rules.go]`
— read directly this session; confirmed this is a structurally distinct code path from the
per-path matcher in Pattern 1. **This distinction must not be collapsed into one sentence in
the plan** — doing so is the most likely mis-implementation risk in this phase.

### Pattern 3: Brace expansion before `**`-aware match — RULE-01/D-01/D-02
**What:** Patterns like `**/*.{js,ts,tsx}` must be brace-expanded into `{**/*.js, **/*.ts,
**/*.tsx}` BEFORE the `**`-aware glob match runs (not combined into one regex pass), mirroring
OCR's `expandBraces` + `doublestar.Match` split.
**When to use:** `rule_glob.py`'s pattern-normalization step, run once per rule at load time
(cacheable) rather than per file.
**Source:** `[VERIFIED: /Users/christopher/tools/open-code-review/internal/config/rules/system_rules.go]`
— function names `expandBraces`/matching call confirmed by direct read this session.

### Pattern 4: Custom `**`-aware matcher, no `PurePath.full_match` — D-01
**What:** `requires-python = ">=3.12"` [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml
— quote: `requires-python = ">=3.12"`] stays locked; `pathlib.PurePath.full_match` (which would
give `**`-aware matching for free) needs Python 3.13 and is off the table for this floor. A
small hand-written matcher — segment-split on `/`, recursive/iterative match with a `**`
segment consuming zero-or-more path segments — must be built and unit-tested against ported
OCR test cases (D-02).
**When to use:** Any `**` pattern in `rule_glob.py`.
**Source:** `[CITED: docs.python.org/3/library/pathlib.html#pathlib.PurePath.full_match]` (3.13
requirement is documented Python behavior) combined with `[ASSUMED]` that no third-party
stdlib-adjacent shim exists that satisfies REL-03's zero-dependency rule — a custom matcher is
the only compliant choice.

### Pattern 5: Case normalization before matching — D-04
**What:** Both path and pattern are lower-cased before any match attempt, so a mixed-case user
pattern (e.g. `**/*.MD`) still matches lower-case-on-disk paths.
**When to use:** First step inside `rule_glob.py`'s resolution loop, applied uniformly to every
layer/pattern.
**Source:** `[CITED: 03-CONTEXT.md D-04]` — locked decision, no alternative to research.

### Pattern 6: Rule-file safety gate, hard-reject not fallback — RULE-03/D-08
**What:** Resolve symlinks (`Path.resolve()`), require the resolved path to stay under repo
root (reject a symlink escape), restrict extension to `.md`/`.txt`/`.markdown`, cap size at
512 KB. Any violation REJECTS THE ENTIRE RUN with an actionable error naming the path and
reason — it must NOT silently fall through to the next resolution layer, because a typo'd
`--rule` path silently reviewing under the wrong (or built-in) checklist is a worse failure
mode than a loud error.
**When to use:** Immediately after a rule path is resolved, before its content is read into
the prompt.
**Source:** `[CITED: 03-CONTEXT.md D-08]`, pattern itself: `[ASSUMED]` — the specific
symlink-then-boundary-check ordering is standard path-traversal-prevention practice but was
not independently verified against an OCR Go equivalent this session (OCR's rule-file read
path was not read; only `system_rules.go`'s resolution/matching logic was read directly).

### Pattern 7: Class-allowlist bypass for gates A/B only — D-09/REV-01
**What:** General profile relaxes ONLY gates A (no real attacker/reachability) and B (no
security impact), and ONLY for findings whose `cls`/defect-class is in a fixed allowlist (NPE,
thread-safety, resource-leak, error-swallowing, injection). Gates C (wrong layer), D (handled
elsewhere with proof), E (noise floor) are enforced identically in both profiles — never
bypassed.
**When to use:** The profile-branching logic that composes beside/inside the existing gate
pipeline (`phase_gate.py` or a new sibling module).
**Source:** `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md]`
— `EXCLUSION_RULES` block read directly this session; gate letters A-E and their one-line
definitions (no-attacker/no-impact/wrong-layer/handled-elsewhere/noise-floor) confirmed
verbatim in that file.

### Pattern 8: Phase-adversary dispatch shape reused for reflection — D-13
**What:** `SKILL.md` instructs the orchestrating agent to spawn a subagent per unit of work
(there: per phase, phase-adversary; here: per file, reflection filter), using a DIFFERENT
model family / fresh context, then only battle-tested/validated output flows forward, written
to a dedicated ledger. `reflection.py` plays the role `run_phase_checks`/`build_gate_record`
play for phase-adversary: prompt-payload construction, structured-response validation, and
verdict application — with NO direct CLI/API call inside the Python module (invocation always
via the skill layer spawning an agent).
**When to use:** Designing `reflection.py`'s public functions and their call boundary with
SKILL.md.
**Source:** `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/SKILL.md:28-47]` — quote: "phase
output → deterministic pre-check (`run_phase_checks`) → reject unresolvable refs (no agent) →
survivors go to opus phase-adversary (different family, fresh context) → only battle-tested
claims flow forward, written to `kb/gates/<phase>.json`" (paraphrase-collapsed from the
multi-line skill text; the ordering and component names are verbatim as read this session).

### Pattern 9: Never-silent ledger discipline extends existing D-14 pattern — REV-02/D-14/D-15
**What:** `report.py`'s existing `write_review_ledger` already writes `position_reviews` and
`dropped` unconditionally (including the empty case — "No finding was dropped" /
"No finding required position review" rendered explicitly rather than omitted)
[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py:625-626,668-669
— quote: `if not dropped: return f"{DROPPED_FINDINGS_HEADING}\n\nNo finding was dropped.\n"` and
`if not results: return f"{POSITION_REVIEW_HEADING}\n\nNo finding required position review.\n"`].
Reflection's retraction ledger and fail-open marker (D-14/D-15) should extend this SAME
artifact (`artifacts/review_ledger.json`) and the same "always render, explicit zero-case"
convention, rather than inventing a new pattern.
**When to use:** `write_review_ledger`'s extension point for reflection entries.
**Source:** `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py:683-716]`
— full function body read this session; current shape is
`{"position_reviews": [...], "dropped": [...]}` written via `_atomic_write` to
`ws.artifacts / "review_ledger.json"`.

### Anti-Patterns to Avoid
- **Reusing `rule_matcher.py` for path globs:** Explicitly forbidden by spec §4.1 and
  REQUIREMENTS.md's Out of Scope table [CITED: .planning/REQUIREMENTS.md "Reusing content/regex
  rule_matcher.py for path globs | Spec §4.1 pins a separate module"]. `rule_matcher.py` is a
  content/regex ASVS pre-filter, unrelated to path-based rule-doc selection.
  `[VERIFIED: 03-CONTEXT.md code_context — sec_overlay/rule_matcher.py: existing content/regex
  ASVS pre-filter — spec §4.1 explicitly says do NOT reuse it; the new module is rule_glob.py]`
- **Adding a `FindingStatus` member for review-mode concepts:** `models.py`/`evidence.py` are
  frozen, byte-mirrored by the Go port (D-11); `positioning.py`'s own docstring states this
  explicitly for `PositionResult`
  `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/positioning.py — module
  docstring quote: "Returns the phase's own result type rather than a models.FindingStatus
  member — models.py is the frozen milestone contract and has no review-position member."]`.
  The same constraint applies to any new reflection/general-profile field.
- **Fuzzy/difflib matching for positioning or reflection snippet checks:** `positioning.py` uses
  exact consecutive-string matching only
  `[VERIFIED: .planning/STATE.md decision log — quote: "positioning.py uses exact consecutive-
  string matching only; no difflib, no fuzzy-match-as-exact risk"]`; reflection's snippet
  handling should follow the same discipline unless the spec explicitly calls for fuzz.
- **Silent fallback on a rule-file safety violation:** D-08 explicitly forbids falling through
  to the next resolution layer on a symlink/extension/size violation — the run must reject
  loudly.
- **Collapsing per-path layer fallthrough (Pattern 1) and whole-layer selection (Pattern 2)
  into one mental model:** the single most likely implementation defect in this phase per this
  session's OCR reading; document both explicitly and test both explicitly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| `**`-aware glob semantics from scratch, guessing edge cases | A brand-new glob algorithm invented ad hoc | Byte-mirror OCR's `system_rules.go` `expandBraces` + `doublestar`-equivalent match, porting its test cases (D-02) | OCR's semantics are field-tested; divergence is explicitly called a defect (D-02) — this is a porting task, not a design task |
| Reflection filter LLM-response trust boundary | Trusting the LLM's own claim that a protected-subject veto was honored | Mechanically re-check protected-subject vetoes in `reflection.py` code, independent of prompt instructions (D-16) | LLM output is advisory for retraction; the code is the actual enforcement boundary — this mirrors the existing findings_gate.py principle that only mechanical receipts confirm |
| Rule-doc content authoring | Writing 9 new checklists from scratch | Port OCR's existing per-language rule docs (`rule_docs/*.md`), preserving their terse imperative format (D-05) | These are field-tested prompt payloads; rewriting them in STE100 prose would change their behavior as LLM instructions, which is explicitly forbidden by D-05 |
| `--exclude` layer-selection logic | A new bespoke merge algorithm | Byte-mirror OCR's `FileFilter` whole-layer-wins semantics (Pattern 2) | Same rationale as glob semantics — OCR's behavior is the spec |

**Key insight:** Nearly everything non-trivial in this phase already has a working, tested Go
implementation sitting in the same filesystem (`/Users/christopher/tools/open-code-review/`).
The engineering risk is not "can this be built" but "was it ported faithfully" — treat every
divergence from OCR as a bug until proven otherwise (D-02).

## Common Pitfalls

### Pitfall 1: Conflating rule-matching resolution with exclude-filter resolution
**What goes wrong:** A planner/implementer reads "first-non-empty layer wins" (true for
`--exclude`/`FileFilter`) and applies it to rule-doc MATCHING too, producing a resolver that
picks one layer and never falls through — silently ignoring project/global/built-in rules for
paths the custom layer doesn't cover.
**Why it happens:** Both are called "resolution" in casual spec language; OCR's actual Go code
implements them as two different functions with different fallthrough behavior.
**How to avoid:** Implement and test them as two explicitly separate functions/code paths; the
rule-matching resolver must have a test where layer 1 has SOME rules but none matching path X,
and the test asserts layer 2 is consulted for path X.
**Warning signs:** A single `resolve()` function handling both `--rule`/`.sec-overlay/rule.json`
matching AND `--exclude` in the same loop is a signal the distinction was missed.

### Pitfall 2: Treating brace expansion and `**` matching as one regex
**What goes wrong:** Writing one big regex that tries to handle both `{a,b,c}` alternation and
`**` recursive-segment matching in a single compiled pattern, which is fragile and diverges
from OCR's two-step approach at edge cases (nested braces, `**` adjacent to a brace group).
**Why it happens:** It looks like it should be "just regex", and combining feels like fewer
lines of code.
**How to avoid:** Expand braces into N concrete patterns first (a list), THEN run the
`**`-aware matcher against each expanded pattern; port OCR's test fixtures to confirm parity
at each stage independently (D-02).
**Warning signs:** A single function taking a raw un-expanded pattern string and doing both
jobs internally.

### Pitfall 3: Assuming Python 3.13 is available and skipping the custom matcher
**What goes wrong:** Since the local dev machine has Python 3.13.14 installed
`[VERIFIED: local env probe this session — `python3 --version` → `Python 3.13.14`]`, an
implementer might reach for `pathlib.PurePath.full_match` "since it works here", breaking the
locked `>=3.12` floor (D-01) for any user on 3.12.
**Why it happens:** Local capability and the project's supported floor are different things;
the temptation to use the nicer stdlib API is real.
**How to avoid:** CI/test matrix (or at minimum a code-review checklist item) should verify no
`full_match` call exists in `rule_glob.py`; the D-03 floor-decision comment in `pyproject.toml`
should be added FIRST as a guardrail/reminder.
**Warning signs:** Any import of `full_match` or reliance on `PurePath.match` behavior specific
to 3.13+.

### Pitfall 4: Silent fallback on rule-file safety violation
**What goes wrong:** A resolver that hits a symlink-escape or oversized rule file quietly falls
back to the built-in default rule doc instead of hard-erroring, masking a user's typo'd
`--rule` path and reviewing with the wrong checklist without any signal.
**Why it happens:** "Fall back to default" feels defensive/graceful, matching a general
instinct to keep the pipeline running.
**How to avoid:** D-08 is explicit: reject the run with an actionable error naming path and
reason. Write a test asserting the run's exit code/error message on each of the three
violation types (symlink escape, bad extension, oversize) — none should exit 0 with a
default-rule fallback.
**Warning signs:** A `try/except` around the rule-file safety check that swallows the
exception and returns a default value.

### Pitfall 5: Inventing an `"unconfirmed"` FindingStatus enum member
**What goes wrong:** REV-03/D-12 name `unconfirmed` as a disposition; a straightforward
reading might add `FindingStatus.UNCONFIRMED` to `models.py`.
**Why it happens:** It is the most direct-sounding implementation of the requirement text.
**How to avoid:** D-11 is explicit — the defect class (and by extension this disposition
concept) rides in a NEW field in the review-mode payload/ledger, in NEW modules, never in
`models.py`. Confirm with the CONTEXT owner (flagged as an Open Question below) exactly which
new module/field carries this value before implementation starts.
**Warning signs:** Any diff touching `models.py`'s `FindingStatus` enum during this phase is
itself the warning sign — D-11 makes such a diff a defect by definition.

## Code Examples

Verified patterns from the actual repo (not OCR, not external docs — this session's direct
reads of the files this phase extends):

### Existing gate ladder text the security profile must reproduce exactly
```
Source: plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md (EXCLUSION_RULES block, read directly this session)
Gate A: no real attacker / no reachability shown
Gate B: no security impact
Gate C: wrong layer
Gate D: handled elsewhere, with proof
Gate E: noise floor
```
(The exact prose wording lives in `prompt-constants.md`; the planner should read the file
directly rather than rely on this paraphrase when writing the security-profile task's
acceptance criteria, since gate letter-to-description mapping is load-bearing for REV-01's
"reproduces current gate behavior exactly" requirement.)

### Existing dropped/decline ledger writer to extend, not replace (REV-02/D-14)
```python
# Source: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py:683-716 (read verbatim this session)
def write_review_ledger(ws: Workspace, *, position_reviews: list[PositionResult], dropped: list) -> Path:
    ledger = {
        "position_reviews": [
            {
                "state": "needs-position-review",
                "claimed_path": r.claimed_path,
                "claimed_line": r.claimed_line,
                "snippet": r.snippet,
                "reason": r.reason,
            }
            for r in position_reviews
        ],
        "dropped": [asdict(d) if is_dataclass(d) else d for d in dropped],
    }
    path = ws.artifacts / "review_ledger.json"
    _atomic_write(path, json.dumps(ledger, indent=2))
    return path
```
Reflection's retraction/fail-open entries should be added as new keys in this same dict
(e.g. `"reflection_retractions"`, `"reflection_skipped"` — exact names are Claude's Discretion
per CONTEXT.md), keeping the single-artifact, single-write-site convention intact.

### Existing `run_review` integration point where profile branching composes
```python
# Source: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:91-160 (read verbatim this session)
def run_review(base: str, head: str, root: str, *, runner=None) -> int:
    ...
    _kept, dropped, declines = review_position_gate([], hunks_by_path)
    write_report(ws, dropped=dropped, position_reviews=declines)
    ...
```
Note the finding list passed to `review_position_gate` is currently `[]` — "No finding source
is wired into `review` mode yet" per the function's own docstring
`[VERIFIED: cli.py:95-98 — quote: "No finding source is wired into review mode yet
(investigate integration lands in a later plan); the gate runs against an empty finding list
so its wiring is exercised now."]`. Phase 3 is where rule resolution + reflection + profile
gating must be wired into this call site to actually produce findings for the review verb;
this is a bigger integration surface than the phase description alone suggests, and the
planner should size a task for "wire a real finding-producing path into run_review" explicitly,
not assume it already exists.

## Runtime State Inventory

Not applicable — this is a greenfield-additive phase (new modules, new rule docs, new CLI
flags), not a rename/refactor/migration. No stored data, live service config, OS-registered
state, secret/env-var renames, or stale build artifacts are implicated by adding `rule_glob.py`,
`reflection.py`, or the `rule_docs/` directory.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Rule-file safety check order (symlink resolve → boundary check → extension → size) is standard path-traversal-prevention practice, not independently confirmed against an OCR Go equivalent this session | Architecture Patterns, Pattern 6 | Low — the four checks themselves are locked by D-08/RULE-03; only the internal ordering is assumed, and any correct ordering satisfies the requirement as long as all four checks run before the file is read |
| A2 | `"unconfirmed"` (REV-03/D-12) lands as a new field in a new review-mode module/payload, most likely alongside or inside `review_ledger.json`, with the underlying `Finding.status` remaining a frozen-contract value | Common Pitfalls Pitfall 5, Open Questions Q1 | Medium — if the planner locks a specific field name/location without owner confirmation, a later correction could touch the same module twice; does not risk touching `models.py` since D-11 is unambiguous on that point |
| A3 | No third-party stdlib-adjacent package exists that would satisfy `**`-aware matching under Python 3.12 without violating REL-03's zero-new-dependency rule | Architecture Patterns, Pattern 4 | Low — even if one existed, REL-03 forbids adding it regardless; the custom matcher is required either way |

**If this table is empty:** N/A — see rows above.

## Open Questions (RESOLVED)

All three questions were resolved during planning on 2026-08-18. Each carries its
resolution inline below. No question remains open for execution.

1. **Where exactly does the `"unconfirmed"` disposition value live?**
   - What we know: `models.py`'s `FindingStatus` enum, `evidence.py`'s
     `SHIPPING_STATUSES`/`runtime_disposition` closed enum, and `prompt-constants.md`'s
     `EVIDENCE_VOCABULARY` block were all read directly this session; none contains the
     literal string `"unconfirmed"` anywhere. D-11 mandates new review-mode fields live in
     new modules, never `models.py`.
   - What's unclear: The exact module/field name that will carry this value (e.g. a
     `disposition` field on a new review-mode payload dataclass, vs. a new key inside
     `review_ledger.json`, vs. something in a not-yet-created `review_report.py`).
   - Recommendation: Planner should surface this as an explicit design decision in the first
     plan touching D-11/D-12 (likely the REV-03 task), naming the exact field/module before
     implementation, rather than let each task guess independently.
   - **RESOLVED** (2026-08-18): Plan 03-04 Task 1 is a `checkpoint:decision` that names the
     exact module and field before any code is written, with the candidate placements as its
     options. Plan 03-05 Task 3 then implements the chosen name in the receipt-gate
     disposition ladder. `models.py` stays frozen either way, per D-11.

2. **Has OCR's rule-file safety-check implementation itself been read for exact ordering?**
   - What we know: `system_rules.go`'s MATCHING/resolution logic was read directly and
     confirmed (Patterns 1-3). The file-safety-read code path (symlink/extension/size) inside
     OCR was NOT read this session — only the CONTEXT.md-level decision (D-08) was used.
   - What's unclear: Whether OCR implements the four checks in a specific order that matters
     for an edge case (e.g. a symlink pointing to an oversized file — does OCR check size
     before or after resolving the symlink target?).
   - Recommendation: If byte-mirroring OCR is a hard requirement even for this safety-check
     (not just the matcher), read OCR's rule-file-loading Go source before finalizing
     `rule_glob.py`'s check order; otherwise D-08's four checks in any order satisfy RULE-03
     as currently worded.
   - **RESOLVED** (2026-08-18): Byte-mirroring is required for the matcher only (D-02), not
     for the safety check. Plan 03-02 Task 3 fixes the order as symlink resolve → repo-root
     boundary → extension allowlist → size cap, documents that ordering and its divergences
     from OCR in the module docstring, and covers the symlink-to-oversized-file edge case with
     a test. Any correct ordering satisfies RULE-03; this one is now locked so tasks do not
     each pick their own.

3. **What finding source feeds `review_position_gate` once Phase 3 lands?**
   - What we know: `run_review` currently calls `review_position_gate([], hunks_by_path)` with
     a hardcoded empty list; the docstring states investigate-integration is deferred to "a
     later plan."
   - What's unclear: Whether Phase 3 itself is the "later plan" that wires a real
     finding-producing path (rule-doc-guided LLM review per file) into this call site, or
     whether that wiring is Phase 4/5's job and Phase 3 only builds the rule resolution +
     reflection + profile machinery in isolation with unit tests.
   - Recommendation: Re-read `.planning/ROADMAP.md`'s Phase 3 success criteria alongside this
     finding before planning; if ambiguous, ask the milestone owner directly — this changes
     whether Phase 3 needs an end-to-end `run_review` integration task or can stop at
     unit-tested modules.
   - **RESOLVED** (2026-08-18): Phase 3 is the wiring phase. ROADMAP Phase 3 success criterion
     4 requires `--profile general` to surface findings that `--profile security` drops on the
     same diff, which is unreachable while the call site passes an empty list. Plan 03-06
     (wave 6) adds the finding source: `review_agent.py` renders the resolved rule doc into a
     per-file prompt at `{{system_rule}}`, SKILL.md dispatches one review-file subagent per
     file and records each return to disk, and `run_review` parses those returns into findings
     that enter `review_position_gate`. Phase 4/5 build on that seam rather than creating it.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All modules | ✓ | 3.13.14 (local) `[VERIFIED: local env probe this session]` | — locked floor stays `>=3.12` per D-01 regardless of local capability; do not use 3.13-only APIs |
| uv | Test/lint running (project convention) | ✓ | 0.11.32 `[VERIFIED: local env probe this session]` | — |
| semgrep | `test_cli_e2e.py`'s scan-fixture tests (unrelated to Phase 3's review-mode tests but shares the test suite) | Not probed this session | — | Tests are `pytest.mark.skipif(shutil.which("semgrep") is None, ...)` — self-skipping, no blocker for Phase 3's own new tests |
| OCR local source | Reference for byte-mirroring (D-02) | ✓ | n/a (Go source tree) at `/Users/christopher/tools/open-code-review/` | If this path becomes unavailable, the milestone spec at `/Users/christopher/Workspace/review_open-code-review/spec_sec-overlay-improvement_20260816_0920.md` is the fallback authority per CONTEXT.md canonical_refs, but CONTEXT.md itself says: "Outside the repo; if unreachable at planning time, stop and ask." |

**Missing dependencies with no fallback:** none identified — this phase is stdlib-only.
**Missing dependencies with fallback:** none blocking; semgrep absence self-skips unrelated tests.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing repo convention) |
| Config file | none found dedicated to pytest config beyond `pyproject.toml`'s standard section (not independently re-confirmed this session; existing test suite runs today per STATE.md's per-plan metrics) |
| Quick run command | `pytest tests/test_rule_glob.py -x` (once created) / `pytest tests/test_reflection.py -x` (once created) |
| Full suite command | `pytest` (repo-wide, matches existing convention referenced in STATE.md decision log) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RULE-01 | `rule_glob.py` matches lower-cased paths, ordered PathRules, brace expansion, `**`-aware, first-match-wins else default | unit | `pytest tests/test_rule_glob.py -x` | ❌ Wave 0 |
| RULE-02 | Layer resolution: per-path fallthrough for matching (Pattern 1); whole-layer selection for `--exclude` (Pattern 2) | unit | `pytest tests/test_rule_glob.py -k layer -x` | ❌ Wave 0 |
| RULE-03 | Rule-file safety: symlink resolve, repo-root boundary, extension allowlist, 512 KB cap, hard-reject | unit | `pytest tests/test_rule_glob.py -k safety -x` | ❌ Wave 0 |
| RULE-04 | `merge_system_rule: true` concatenates built-in + user text under fixed headers | unit | `pytest tests/test_rule_glob.py -k merge -x` | ❌ Wave 0 |
| RULE-05 | 9 per-language rule docs exist, cover NPE/thread-safety/injection/resource-leak/error-swallowing with exclusions | smoke (content presence) | `pytest tests/test_rule_docs.py -x` | ❌ Wave 0 |
| REV-01 | `--profile security` reproduces gate A-E exactly; `--profile general` bypasses A/B only for allowlisted classes, C/D/E always enforced | integration (dual-run fixture, D-10) | `pytest tests/test_review_profiles.py -x` | ❌ Wave 0 |
| REV-02 | Reflection filter: retract-only, fail-open, protected-subject vetoes enforced in code | unit + integration | `pytest tests/test_reflection.py -x` | ❌ Wave 0 |
| REV-03 | Receipt gate remains sole `confirmed` authority; general-defect findings without Tier-1 receipt ship `unconfirmed`/`needs-deployment-testing` | unit (extends existing `findings_gate.py`/`evidence.py` tests) | `pytest tests/test_findings_gate.py -k general_defect -x` | ❌ Wave 0 (new cases in existing file) |

### Sampling Rate
- **Per task commit:** targeted `pytest tests/test_<new_module>.py -x`
- **Per wave merge:** `pytest` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_rule_glob.py` — covers RULE-01, RULE-02, RULE-03, RULE-04 (new file; confirmed absent via `ls tests/` this session)
- [ ] `tests/test_rule_docs.py` (or equivalent content-presence check) — covers RULE-05 (new file)
- [ ] `tests/test_reflection.py` — covers REV-02 (new file; confirmed absent via `ls tests/` this session)
- [ ] `tests/test_review_profiles.py` — covers REV-01's dual-run regression fixture (D-10) (new file)
- [ ] New test cases inside existing `tests/test_findings_gate.py` — covers REV-03's general-defect-without-receipt path (extend, don't replace)
- [ ] `rule_docs/` fixture data for tests (ported OCR sample rule files, or a minimal synthetic set covering brace/`**` edge cases per D-02's "port OCR test cases where they exist")

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | Not applicable — no auth surface in this phase |
| V3 Session Management | no | Not applicable |
| V4 Access Control | no | Not applicable — single-user CLI tool |
| V5 Input Validation | yes | `--rule`/`--exclude` CLI args and resolved rule-file paths must be validated (symlink resolve + repo-root boundary check, D-08) before being read as prompt content; this is itself a path-traversal control, not a general-purpose validation library — hand-rolled per D-08/RULE-03, matching the existing `DIFF-01` ref-regex validation pattern in `cli.py`/`diffscope.py` |
| V6 Cryptography | no | Not applicable — no crypto operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Symlink escape via `--rule`/resolved rule.json paths pointing outside repo root | Tampering / Information Disclosure | Resolve symlinks then boundary-check against repo root before reading file content (RULE-03/D-08) — reject, do not silently fall back |
| Oversized rule-file DoS (a malicious/misconfigured rule.json pointing at a huge file, bloating the LLM prompt or memory) | Denial of Service | 512 KB size cap, hard-reject on violation (RULE-03) |
| Extension smuggling (a `.py`/`.sh` file loaded as "rule content" and injected verbatim into an LLM prompt) | Tampering | Extension allowlist restricted to `.md`/`.txt`/`.markdown` (RULE-03) |
| Prompt injection via untrusted rule-doc content reaching the LLM (a project's `.sec-overlay/rule.json` pointing at attacker-controlled text in the reviewed repo) | Tampering / Elevation of Privilege | Out of this phase's explicit scope per CONTEXT.md, but worth flagging: rule docs are LLM prompt payloads (D-05) read from the TARGET repo's own `.sec-overlay/` directory for the project layer — a hostile PR could modify `.sec-overlay/rule.json` to inject arbitrary prompt content into the reviewer's own instructions. `[ASSUMED]` — no existing mitigation for this was found in CONTEXT.md or the code read this session; flag as an open question for the milestone owner rather than assume out of scope silently. |
| Reflection filter over-trusting LLM retraction claims (an LLM claiming a protected-subject veto was satisfied when it was not) | Tampering / Repudiation | D-16: protected-subject vetoes mechanically re-checked in code, never trusted from LLM output alone |
| Reflection filter silent failure masking real findings | Denial of Service (of the finding, from the user's perspective) | D-15: fail-open events explicitly logged (`reflection-skipped` marker) in report and JSON — never a silent drop |

## Sources

### Primary (HIGH confidence)
- `[VERIFIED: /Users/christopher/tools/open-code-review/internal/config/rules/system_rules.go]`
  — read directly this session; rule-matching per-path fallthrough vs. exclude whole-layer
  selection, brace expansion before `**` match.
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md]` — read
  directly this session; `EXCLUSION_RULES` gates A-E, `EVIDENCE_VOCABULARY` (Tier-1/Tier-2
  receipts, `SHIPPING_STATUSES`, `runtime_disposition` enum — no `"unconfirmed"` value present).
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/SKILL.md:28-47]` — read directly this
  session; phase-adversary dispatch shape.
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/positioning.py]` —
  read directly this session (full file, 219 lines).
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffhunks.py]` — read
  directly this session (full file, 151 lines).
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/file_select.py]` —
  read directly this session (full file, 202 lines).
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py]`
  — read directly this session (full file, 171 lines).
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/exclusions.py]` — read
  directly this session (full file, 75 lines).
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py]` — read
  directly this session (full file, 751 lines) — `write_review_ledger`, `render_dropped_findings_section`,
  `render_position_review_section`, `write_report`.
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py]` — read
  directly this session (full file, 262 lines) — `run_review`, `main`'s `review` subparser.
- `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml]` — read directly
  this session (Bash `cat`) — `requires-python = ">=3.12"`, `dependencies = []`.
- `[VERIFIED: .planning/config.json]` — read directly this session — no `nyquist_validation`
  key.
- `[VERIFIED: .planning/REQUIREMENTS.md]` — read directly this session — RULE-01..05, REV-01..03
  exact wording, Out of Scope table, Traceability table.
- `[VERIFIED: .planning/STATE.md]` — read directly this session — decision log entries on
  `PositionResult`, `review_ledger.json` rationale, coverage manifest shape.
- `[VERIFIED: .planning/phases/03-rule-matching-review-modes/03-CONTEXT.md]` — read directly
  this session (full file) — all D-01..D-16 decisions, canonical refs, code context.

### Secondary (MEDIUM confidence)
- `[CITED: docs.python.org/3/library/pathlib.html#pathlib.PurePath.full_match]` — standard
  documented Python 3.13 requirement for `full_match`, not independently re-verified via a
  fresh fetch this session (training knowledge of a well-established stdlib API boundary,
  cross-checked against the locked D-01 decision text which independently states the same
  3.13 requirement).

### Tertiary (LOW confidence)
- `[ASSUMED]` Rule-file safety-check internal ordering (Pattern 6, Open Question 2) — not
  verified against OCR's actual file-loading Go source this session.
- `[ASSUMED]` Prompt-injection-via-rule-doc threat (Security Domain table) — flagged as a gap,
  not confirmed as in- or out-of-scope by any read document.
- `[ASSUMED]` Exact field/module name for the `"unconfirmed"` disposition value (Assumption
  A2, Open Question 1).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, stdlib-only confirmed directly in `pyproject.toml`.
- Architecture: HIGH — every integration point (`cli.py`, `report.py`, `phase_gate.py`,
  `positioning.py`) was read directly this session; the two resolution-pattern distinction
  (Pattern 1 vs Pattern 2) was independently confirmed by reading OCR's Go source directly.
- Pitfalls: HIGH — five pitfalls identified, four grounded in directly-read source (OCR Go
  code, this repo's frozen-contract docstrings, D-08's explicit text), one (Pitfall 3) grounded
  in a directly-run environment probe.
- Vocabulary/disposition naming (`"unconfirmed"`): LOW — confirmed ABSENT from all three
  authoritative closed-vocabulary sources checked; flagged as an Open Question rather than
  resolved.

**Research date:** 2026-08-18
**Valid until:** 2026-09-17 (30 days — stable internal codebase + a locally-pinned OCR
reference; re-verify sooner if `models.py`/`evidence.py` or OCR's `system_rules.go` change)
