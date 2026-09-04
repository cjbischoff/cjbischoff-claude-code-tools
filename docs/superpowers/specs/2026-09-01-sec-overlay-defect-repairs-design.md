# sec-overlay defect repairs — build spec

Date: 2026-09-01. Branch: `docs/sec-overlay-defect-repairs-spec`.

## 1. Scope and authority

This spec drives a repair of 22 requirements against the sec-overlay plugin. Four observation
documents supply the input:

1. `/Users/christopher/Workspace/review_comply/report_secoverlay-comply-defects_20260823_2004.md`
   — the defect register, 96 entries.
2. `/Users/christopher/Workspace/review_comply/report_secoverlay-comply-eval_20260823_2028.md`
   — the run evaluation.
3. `/Users/christopher/Workspace/review_comply/analysis_secoverlay-comply-coverage_20260823_1612.md`
   — the coverage analysis.
4. `/Users/christopher/Workspace/review_comply/audit_secoverlay-comply-transcript_20260823_1526.md`
   — the evidence transcript.

`/Users/christopher/Workspace/review_enforce/spec_secoverlay-improvements_20260823_1219.md` is the
prior spec. It owns REQ-01 through REQ-34 and RC-1 through RC-8. This spec never reuses one of
those identifiers.

**The source tree is the authority, not the register.** The register measured plugin version
1.107.3. The source tree is at version 1.122.0, fifteen minor versions later. Every requirement
below cites a line opened in the source tree this session. A register citation that no longer
resolves is recorded as drift in Section 2 and is not carried forward.

Out of scope:

- Register entries the register itself withdrew.
- Register entries this session proved fixed.
- The two Comply-repository remediation items in the evaluation. The stray commit `7045a051b`
  is target-repository cleanup, not a plugin defect.

The deliverable of the session that produced this file is the specification only. No plugin code
changed.

All paths are relative to `plugins/sec-overlay/skills/sec-overlay/` unless stated otherwise.

## 2. Cite verification record

The register maps its citations to the installed copy under `~/.claude/plugins/cache/` at plugin
version 1.107.3. Each citation below was mapped onto the source tree and opened there.

### Table A — Verified, no drift

| Defect | Location | Content confirmed |
|--------|----------|-------------------|
| D-B91-b | `phases.py:140`, `:142`; `report.py:679`, `:270` | `report` runs at index 20 and `redteam` at index 22. `report.py` probes `redteam-plan.md` with `.exists()` and always prints a link to it. |
| D-B78-b | `phases.py:130`, `:131` | `validate` runs at index 13, before `trace` at index 14. |
| D-B77-a | `phases.py:135`; `driver.py:307-309` | `factcheck` declares no inputs and no outputs. No phase produces `kb/verdicts.json`. |
| D-B77-b | `driver.py:313-317` | An invalid verdict and an unmatched verdict are both dropped with no record. |
| D-B79-a, D-B74-a | `cli.py:1073`; `scanscope.py:113`, `:121` | `write_scan_scope` and `load_scope` exist. No audit path calls either. |
| D-B85-a | `sarif.py:92-109` | A SARIF result carries five fields. It carries no `affected_sites` and no `relatedLocations`. |
| D-B85-b | `sarif.py:107`; `artifact_consistency.py:175` | Every needs-runtime finding is suppressed with kind `inSource`. No consistency clause compares SARIF to the report. |
| D-B93-b | `postflight.py:67`, `:76`, `:91` | `run_postflight` accepts `changed_files`. Every caller omits it, so the drift filter always receives an empty set. |
| D-B95-b | `dedupe.py:14`; `postflight.py:44` | `_ACTIVE` holds `RAW` and `CONFIRMED` only, so a rejected finding is never fingerprinted and falls back to a colliding `file:line:cls` key. |
| D-B87-a | `selfscore.py:18`, `:46` | `_REPORTED` holds `CONFIRMED` and `FIXED`. The counters never call `collapse_clusters`, and `duplicate` has no key. |
| D-B89-a | `redteam.py:251` versus `:182` | The group heading reads the finding-level `preconditions`. The directive body reads the runtime dictionary's `preconditions`. |
| D-B80-b | `verify.py:349`, `:392` | `verify` reads every finding, then writes the whole set back. No barrier separates the read from the write. |
| D-B83-a | `verify.py:287` | The oracle matches on `os.path.basename(file)`. A `ponytail:` comment names the aliasing ceiling. |
| D-B75-a | `agents/trace.md:27-28` | The declared blocker taxonomy omits `external-boundary`. |
| F-3 schema | `references/finding.schema.json`; `schema.py:49-64` | 43 properties, 4 with an `enum`. `additionalProperties: false` is declared. `schema.py` implements `type`, `enum`, `items`, `required`, and `properties` only. |
| D-B72-a | `evidence.py:15-24` | `TIER1_RECEIPTS` and `TIER2_RECEIPTS` partition `_MECHANICAL`. The prefixes `read:` and `llm-claimed:` fall outside both tiers. |

### Table B — Verified, drift recorded

| Defect | Status now | Evidence |
|--------|-----------|----------|
| D-B79-c | Fixed | `tests/test_prompt_tokens.py` derives the dispatched prompt set from `PHASE_TABLE` and asserts every `{{TOKEN}}` is in `DISPATCH_TOKENS`. |
| D-B80-a | Fixed | `verify.py:306` reads the profile's planned rulesets; `:350` calls it. |
| D-B83-c | Fixed | `verify.py` appends `verify:cause:<cause>` on every outcome. |
| D-B83-d | Half fixed | `report.py:333-373` omits an absent measurement. `cost.record_agent` still has no non-test caller, so the token measurement never exists. |
| D-B91-a | Fixed | `prove.py:175` writes `runtime_disposition = "static-settled"`. |
| D-B85-a | Narrowed | `report.py:262-270` renders the affected-sites table. The loss is now confined to SARIF. |
| D-B87-b | Narrowed | `postflight.py:23-29` falls back from `reason` to the event string. |
| D-B79-b | Worse than filed | `verify.py` gates promotion on a `validate-fix:` history event. No phase in `PHASE_TABLE` writes that event, so the branch is unreachable. |
| Prior REQ-30, REQ-31 | Shipped | `prove` is index 23 and `artifact-consistency` is index 26. The register measured 26 phases; the table now holds 28. |

### Table C — Not checked this session

Roughly 60 register entries were not opened. The group is dominated by F-2, the documentation
drift class. Treat every Table C entry as unconfirmed until its owning requirement is built.

One consequence is recorded here because it shapes the build. Every F-2 citation is stale by
construction: two phases landed since the register was written, so every phase index at or after
`validate` shifted. Repairing F-2 as 18 individual document edits would restate 18 facts that can
drift again. REQ-61 replaces the class with one generator and one contract test.

## 3. Root causes

Seven causes carry work. RC-1 through RC-8 belong to the prior spec; RC-3 and RC-5 are reused
here because new members joined them. RC-9 through RC-14 are new.

**RC-9 — a phase reads an artifact that has no producer, or whose producer runs later.**
Members: D-B91-b, D-B78-b, D-B77-a, D-B79-b, D-B80-b. Invariant: every artifact a phase reads
has at least one producer, and that producer is earlier in `PHASE_TABLE`. A phase that both
reads and writes the finding set satisfies the invariant through its earlier producer.

**RC-10 — deferred.** No member was verified this session. Its four F-4 members sit in Table C.

**RC-11 — two readers compute the same quantity from different fields or different populations,
and nothing compares them.** Members: D-B87-a, D-B89-a, D-B85-b. The home for the repair is the
existing `artifact-consistency` gate, extended with clauses (g), (h), and (i).

**RC-12 — a declared constraint has no enforcer.** Members: `additionalProperties: false`; 39 of
43 open vocabularies; the receipt-prefix set at `references/prompt-constants.md:157-159` against
`evidence.py:15-24`; the unreachable rule at `agents/validate.md:86`; the prose request at
`agents/trace.md:34-39`.

**RC-13 — a systemic cluster survives in one consumer and is dropped by the rest.** Members:
D-B85-a, now SARIF-only, and D-B95-b.

**RC-14 — a capability is implemented, documented, and never called.** Members:
`postflight.py:76` `changed_files`; `cost.record_agent`; `write_scan_scope` and `load_scope`;
`scoring.score_fix`; the fact-check agent named at `driver.py:298-302`.

**RC-3 reused — documented contracts drift from code.** Members: the roughly 18 F-2 entries.

**RC-5 reused — verify is imprecise and non-deterministic across configurations.** Members:
D-B83-a, D-B83-b.

Build order: RC-9, RC-14, RC-12, RC-11, RC-13, RC-5, RC-3. RC-9 runs first because it is the
only group that changes what the harness concludes. RC-3 runs last because generating documents
from `PHASE_TABLE` is stable only after the table stops moving.

## 4. Trade-off statement

**Three requirements delete shipped capability instead of finishing it.** `factcheck`, agent
token accounting, and `scan-scope` are each implemented, documented, and unreachable. Finishing
one means writing a producer the harness cannot observe — the orchestrator reports token spend,
the driver does not measure it — or a consumer nothing asks for. Deletion costs a planned
feature and buys a stage ledger that means what it says. The code stays in git history.

**This is therefore a major version bump.** Removing a phase name, a CLI-callable module, and a
documented prompt token breaks the plugin's contract. The plugin goes to `2.0.0` with a
`BREAKING CHANGE:` footer.

**REQ-40 and REQ-43 change the phase order.** A workspace resumed from a 1.x run carries stage
keys in the old order and re-runs phases. This is accepted. No resume-across-version guarantee
exists today.

**Schema closure fails runs that pass today.** That is the intent. The first run after REQ-49
and REQ-50 produces a wave of gate errors from findings that were always malformed. Both
requirements are sequenced last inside their group so the prior REQ-27 quarantine path absorbs
them.

**The callerless-helper guard carries an allowlist, and an allowlist rots.** REQ-48 requires a
one-line reason for each entry and fails when an allowlisted entry gains a caller.

## 5. Build groups

Requirement numbering starts at REQ-40. REQ-35 through REQ-39 are left unused; the prior spec
names a phantom REQ-35.

### Group 1 — RC-9: a phase reads only what an earlier phase produced

| Requirement | Target | Change | Acceptance test |
|---|---|---|---|
| REQ-40 | `phases.py:140-142`; `report.py:270`, `:524-529`, `:679` | Move `redteam` before `report`. Declare `_redteam_plan` as a report input. Delete the `has_redteam_plan` existence probe. | The report names no file absent from the run. No `.exists()` probe remains in `report.py`. |
| REQ-41 | `agents/validate.md:86`; `calibrate.py` | Move the external-boundary ban out of the validate prompt. Enforce it in `calibrate`, which runs at index 16, after `trace`. | A confirmed finding whose reachability blocker is `external-boundary` is demoted by `calibrate`. The unreachable prompt rule is gone. |
| REQ-42 | `phases.py:132-135`; `driver.py:295-317`; `factcheck.py`; `agents/factcheck.md` | Delete the phase. Its only input has no producer, and it records `done` while doing nothing. | No run records a `factcheck` stage key. The module and the prompt are gone. The documents no longer name the phase. |
| REQ-43 | `phases.py:137-138`; `scoring.py`; `SKILL.md:521-523` | Add the `validate-fix` agent phase between `patch` and `verify`, with output `kb/gates/validate-fix.json`. Write its receipt through `score_fix`. | The `verify:conflict` branch at `verify.py:363-371` is reachable. `score_fix` has a non-test caller. |
| REQ-44 | `verify.py:349`, `:392`; `workspace.py:130-144` | Re-read the finding set and merge by id immediately before write-back, instead of writing a stale whole-set snapshot. | A finding written between verify's read and its write survives the write-back. |

### Group 2 — RC-14: wire the lever or delete it

| Requirement | Target | Change | Acceptance test |
|---|---|---|---|
| REQ-45 | `postflight.py:67`, `:76`, `:91`; `driver.py:324` | Pass `changed_files` from the driver, and normalize `where` to a repository-root-relative path before the merge key. Both halves are required. | Control test: mark every file changed and assert that zero items survive. The measured run kept 278 of 312. |
| REQ-46 | `cost.py:17-28`, `:90`; `report.py:352-360`; `SKILL.md:255-261` | Delete `record_agent`, the two token tables, and `estimate_cost_usd`. Keep wall-clock, which `driver.py:97` measures. | No "(measured)" token section can render. `record_agent` is gone. |
| REQ-47 | `scanscope.py`; `cli.py:83`, `:253`, `:276`, `:1073`; five document references | Delete the module. `{{SCAN_SCOPE}}` is absent from `DISPATCH_TOKENS`, so no audit prompt can receive it, and the prior REQ-15 `PATH_BASE` token already covers path normalization. | No `scanscope` import remains. The `agents/README.md:235` row is gone. |
| REQ-48 | new `tests/test_no_dead_helpers.py` | Fail on a public `sec_overlay` function that has no non-test caller. Each allowlist entry carries a one-line reason, and an entry that gains a caller fails the test. | The test fails today on the four helpers above and passes after REQ-45 through REQ-47. |

### Group 3 — RC-12: every declared constraint gets an enforcer

| Requirement | Target | Change | Acceptance test |
|---|---|---|---|
| REQ-49 | `schema.py:49-64` | Implement `additionalProperties`. The schema declares it `false` today and the validator ignores it. | A finding carrying an unknown key fails validation. This is the check that catches D-B93-a `render_stale`. |
| REQ-50 | `references/finding.schema.json`; `models.py:48` | Generate the `enum` for `cls`, `receipt_tier`, `completeness_tier`, `judge_verdict`, and `reachability.blocker` from the Python frozensets. Give `history`, `open_questions`, and `affected_sites` item schemas. | A frozenset and its schema `enum` cannot drift, because the test derives one from the other. |
| REQ-51 | `evidence.py:15-24`; `references/prompt-constants.md:157-159` | Make the frozenset the single source. An unrecognised receipt prefix is an error, not a silent drop. | A finding whose only source is `llm-claimed:` receives no mechanical tier. |
| REQ-52 | `agents/trace.md:27-28`, `:34-39`; `findings_gate.py` | Add `external-boundary` to the declared taxonomy. Check `open_questions` in the gate instead of requesting it in prose. | A traced finding on the external-fact branch with zero `open_questions` is rejected. |

### Group 4 — RC-11: reconcile what two readers count

| Requirement | Target | Change | Acceptance test |
|---|---|---|---|
| REQ-53 | `artifact_consistency.py:175` | Clause (g): the SARIF result count equals the report's rendered finding count. | 27 SARIF results against 25 report rows fails the gate. |
| REQ-54 | `selfscore.py:18`, `:46` | Clause (h): the self-score population equals the report population, with cluster collapse applied on both sides. Give `duplicate` a named key. | The four `duplicate` findings appear under some key. The measured `70 + 22 + 242 ≠ 338` cannot recur. |
| REQ-55 | `redteam.py:251`, `:182` | Clause (i): the group heading and the directive body read one `preconditions` field. | A finding that has preconditions never renders `_not specified_` under a "Code-settled" heading. |
| REQ-56 | `report.py:253`, `:320-332`, `:351`, `:378` | Count the bottom-line severity sentence over the triage population. Never render a status word in the triage "What" column. | A high-severity needs-runtime finding cannot coexist with a "medium/low" bottom line. |

### Group 5 — RC-13: a cluster survives every consumer

| Requirement | Target | Change | Acceptance test |
|---|---|---|---|
| REQ-57 | `sarif.py:92-109`, `:107` | Emit one `relatedLocations` entry per `affected_sites` entry, carry the finding id, and stop using `inSource` for a needs-runtime suppression. | A 66-site cluster produces 66 locations in SARIF, not 1. |
| REQ-58 | `dedupe.py:14`, `:50-53` | Fingerprint every finding, whatever its status. | Two rejected findings at the same `file:line:cls` do not collapse onto one prior-context key. |

### Group 6 — RC-5: the verify oracle

| Requirement | Target | Change | Acceptance test |
|---|---|---|---|
| REQ-59 | `verify.py:166-170`, `:287` | Match the finding's full repository-relative path. Evaluate the sink file when the patch touches the source file instead. | A patch to `file-name-sanitize.ts` that clears a sink in `PackageSetup.ts` verifies. |
| REQ-60 | `verify.py:248-301`; `VERIFY_CAUSES` | Add `rule-no-discriminate` for a rule whose sink list matches both the vulnerable and the safe construction. | A `path.join` to `path.resolve` fix reports the new cause, not `not-fixed`. |

### Group 7 — RC-3: documents generated from the table

| Requirement | Target | Change | Acceptance test |
|---|---|---|---|
| REQ-61 | new generator; `SKILL.md`; four folder READMEs | Emit the phase order, index, kind, prompt, and declared inputs and outputs from `PHASE_TABLE`. Extend the prior REQ-32 contract lint to fail when a document names a phase, an index, or a token absent from `PHASE_TABLE` or `DISPATCH_TOKENS`. | Renaming a phase breaks the test until the documents regenerate. This clears the roughly 18 F-2 entries as a class. |

## 6. Deferred defects

Record these. Do not repair them inside this requirement set.

- RC-10 and its four F-4 members. No member was verified this session.
- Every Table C entry that REQ-61 does not clear. Each is unconfirmed against version 1.122.0.
- The two Comply-repository remediation items in the run evaluation. The stray commit
  `7045a051b` is target-repository cleanup, not a plugin defect.
- `class_extension_status` and any other callerless helper that REQ-48 surfaces but no
  requirement here owns. Add it to the allowlist with a reason, or open a follow-up.

## 7. Verification gates

- Run the full plugin test suite after each group. The baseline is 1766 tests passing at
  plugin version 1.122.0.
- Run `uv run ruff check sec_overlay/ bench/ tests/` and `uv run ty check` after each group.
- REQ-48, REQ-49, and REQ-61 must fail before their repair lands and pass after it. Record both
  results.
- REQ-53, REQ-54, and REQ-55 must block the pipeline on a contradiction, not warn.
- After Group 7, re-run sec-overlay against `/Users/christopher/Workspace/review_comply/Comply`.
  Confirm three outcomes: the report names no absent file, the self-score population equals the
  report population, and the postflight drift filter removes items when files change.

## 8. Commit protocol

- One requirement per red-green pair. The red commit adds the failing acceptance test. The green
  commit adds the code. A single commit holding both skips the red phase.
- Carry the requirement id in both subjects.
- Stage explicit paths only. Never bypass the hooks.
- Bump the plugin version in `plugins/sec-overlay/.claude-plugin/plugin.json` in the same commit
  as any shipping-file change. REQ-42, REQ-46, and REQ-47 each carry a `BREAKING CHANGE:` footer
  and bump major.
- Stage the touched folder's `README.md` in the same commit.
- Run `prek run` before each commit.
- Open a pull request and wait for the CodeRabbit walkthrough comment before merging.

## 9. Definition of done

- All 22 requirements land, each with a passing acceptance test.
- The full suite passes at the end of every group.
- The plugin version reaches `2.0.0`, and the changelog records the three removals.
- No phase reads an artifact whose producer runs later or does not exist.
- `artifact-consistency` carries clauses (g), (h), and (i), and each blocks.
- The document generator runs, and the contract lint fails on a hand-edited phase fact.
- The Comply re-run confirms the three outcomes in Section 7.
- The major-version decision is logged under `docs/decisions.md`.
</content>
</invoke>
