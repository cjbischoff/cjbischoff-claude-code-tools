# sec-overlay improvements — build spec

Date: 2026-08-23. Branch: `feat/sec-overlay-improvements`.

## 1. Scope and authority

This spec drives a build of 29 requirements against the sec-overlay plugin. Three documents
govern it, in this order of authority:

1. The user's build addendum of 2026-08-23. It overrides the requirements document.
2. `/Users/christopher/Workspace/review_enforce/spec_secoverlay-improvements_20260823_1219.md`,
   the requirements document.
3. This spec, which records verified locations and acceptance tests.

Do not invent scope. Build only what the requirements document defines, as corrected by the
addendum.

All paths are relative to `plugins/sec-overlay/skills/sec-overlay/` unless stated otherwise.

### Requirement set

Thirty requirement ids carry work. REQ-19 is the same change as REQ-06, so the build holds 29
distinct changes. Three notes apply:

- REQ-35 is a phantom. Line 81 of the requirements document names "REQ-35 (fenced-build
  escape hatch)", but Part C holds no REQ-35 block. REQ-14 covers that ground.
- REQ-23 folds into REQ-13.
- REQ-26, REQ-28, and REQ-29 have no blocking work.

## 2. Cite verification record

The requirements document maps its line cites to plugin version 1.86.4 at commit `1aedb2e`.
This build targets a later HEAD. I re-verified the cites below against the current working
tree this session. I did not re-verify the cites marked "not checked"; treat those as
unconfirmed until the owning requirement is built.

### Verified, no drift

| Location | Content confirmed |
|----------|-------------------|
| `helpers/sec_overlay/patch_status.py:48-60` | Reverse check runs first, forward check second |
| `references/finding.schema.json:25,27,38` | `evidence_sources`, `verification`, `runtime_disposition` |
| `helpers/sec_overlay/report.py:351` | Literal `"run redteam-plan test"` |
| `agents/trace.md:15` | Filter reads `status == "confirmed"` |
| `agents/validate.md:82-83` | Tier-2 receipts named as sufficient evidence |
| `agents/threat-model.md:8` | Import list without QUALIFIER_PROOF |
| `helpers/sec_overlay/run.py:228,257` | Both count `ws.findings_dir.glob("F-*.json")` |
| `helpers/sec_overlay/driver.py:128` | `{{ATTACK_CLASS}}` joined with commas |
| `helpers/sec_overlay/models.py:154` | `from_dict` drops unknown keys silently |
| `helpers/sec_overlay/dependency_sinks.py:114` | `indicators` parsed into the entry |
| `helpers/sec_overlay/calibrate.py:91,115` | `_precondition_weight` defined and called |
| `references/prompt-constants.md:51-60` | SEVERITY_PRECONDITION block |
| `helpers/sec_overlay/evidence.py:14,17,20,25` | Tier sets and the partition assert |
| `helpers/sec_overlay/profile.py:57,66` | `scan_options` dict; `from_dict` is `cls(**d)` |
| `helpers/sec_overlay/findings_gate.py:139` | Tier-1 required for `confirmed` and `fixed` |

### Verified, drift recorded

| Requirement | Document cite | Actual location |
|-------------|---------------|-----------------|
| REQ-18 | `models.py:79-98` | `runtime_test` is at `models.py:74`, outside the cited range. `open_questions` is at `:88-93`. `affected_sites` is at `:96-98`. |
| REQ-09 | `agents/classes/` "14 files" | 13 class prompts plus `README.md`. A directory scan must exclude `README.md`. |

### Not checked this session

REQ-05, REQ-11, REQ-12, REQ-14, REQ-15, REQ-16, REQ-33. Verify each cite before you build
its requirement, and record any drift in this table.

## 3. Ruling on REQ-09

The requirements document's REQ-09 is wrong against HEAD and must not be built literally.
The addendum supplies the correct build.

**Why the document is wrong.** It claims no mapping from `cls` to its class file exists. One
exists: `_ALIASES` at `helpers/sec_overlay/class_ext.py:13`, resolved by
`class_extension_status` at `class_ext.py:16-42`. It also requires rejecting a `cls` whose
class file is absent. That contradicts the documented design at `class_ext.py:1-5`, where an
uncovered class falls back to the base prompt and the miss is recorded. It would break the
green test at `helpers/tests/test_class_ext.py:18-24`, which asserts that `xxe` produces a
recorded gap. It would reject 16 live classes, including `path-traversal` and
`deserialization`, which REQ-30 lists as auto-confirm classes.

**Build validity, not coverage.**

1. Validate each finding's `cls` against the canonical key set. Reject a `cls` in neither
   part of that set.
2. Keep a missing class file as a recorded gap with disposition `needs_follow_up`. Do not
   change `class_ext.py`'s fall-back-and-record behaviour.
3. Acceptance test: `cls="bogus"` is rejected. `cls="xxe"` is accepted, and is recorded as a
   gap when no file exists. `test_class_ext.py` stays green.

**The canonical key set.** Derive it as a union, so it cannot drift from its sources:

- The 18 keys in the `references/attack-classes.md` table at `:9-26`.
- `set(clsmap.CWE_CLS.values())` from `clsmap.py:15-27`.
- `set(clsmap._RULE_ID_CLS.values())` from `clsmap.py:36-65`.
- The two terminal fallbacks `security-other` and `unknown`, returned by
  `cls_from_semgrep_meta` at `clsmap.py:143,148-149`.

The union holds 29 keys. A hand-written list is not acceptable. The addendum's illustrative
list of extras omits `resource`, `business-logic`, and `excessive-agency`, which
`clsmap.py` also emits; a derived union covers them.

**Sequencing.** Land REQ-09 after REQ-32, not in group 2. REQ-32 makes the canonical key set
a single code constant. REQ-09 validates against that constant, so the two cannot drift.

## 4. Trade-off statement

The proof-by-execution lane (REQ-30) is opt-in (`scan_options.prove_findings`, default off)
and auto-confirms only when a real entrypoint is reachable and the class is oracle-able; a
slice-only proof attaches a human-runnable harness and stays needs-runtime; a fully fenced
target degrades to static confirmation.

## 5. Build groups

Groups land in order. Run the full plugin test suite after each group.

### Group 1 — contract layer

| Requirement | Target | Change | Acceptance test |
|-------------|--------|--------|-----------------|
| REQ-02 | `references/finding.schema.json:27,38`; `helpers/sec_overlay/models.py` | Add enums for `verification` and `runtime_disposition`. Enforce at load. Read allowed values from the schema JSON. Add no dependency. | A finding with an out-of-enum `verification` fails to load. |
| REQ-18 | `references/prompt-constants.md`; `agents/investigate.md` | Publish the `runtime_test`, `open_questions`, and `affected_sites` shapes. Source of truth is `models.py:74,88-93,96-98`. | A contract test asserts the published shapes match the docstrings. |
| REQ-07 | `agents/validate.md:82-83` | State that a Tier-1 receipt is required for `confirmed`. | The prompt text names Tier-1 as required, matching `findings_gate.py:139`. |
| REQ-10 | `agents/threat-model.md:8` | Add QUALIFIER_PROOF to the import list. | The rendered prompt carries QUALIFIER_PROOF. |
| REQ-32 | New test module; new constants module | Single-source the contract constants, including the canonical key set of section 3. Assert five contract properties. | The lint fails when a constant and its document drift apart. |

REQ-32 sits in group 1 by the Part E sequencing. That placement satisfies the REQ-09 ruling,
because REQ-09 lands in group 2 and depends on the REQ-32 constant.

### Group 2 — data integrity

| Requirement | Target | Change | Acceptance test |
|-------------|--------|--------|-----------------|
| REQ-13 | `helpers/sec_overlay/run.py:228,257` | Count from `findings.json`, not the `F-*.json` glob. Add `findings_in` and `findings_out`. | A workspace holding `C-*.json` findings reports a non-zero count. |
| REQ-15 | `run_prefilter` | Emit paths relative to PATH_BASE. | An emitted path is relative to PATH_BASE. |
| REQ-16 | Prefilter phase | Write the receipt before marking the phase done. Skip the done transition on abort. | An aborted prefilter leaves the phase not done. |
| REQ-17 | `helpers/sec_overlay/driver.py:128` | Pass `{{ATTACK_CLASS}}` as a JSON array. | The rendered dispatch carries a JSON array. |
| REQ-08 | `helpers/sec_overlay/driver.py:104` | Add `{{OVERLAY_ROOT}}`, `{{HELPERS_DIR}}`, and `{{FP_FEEDBACK}}` to the substitution map. | A scan of every rendered prompt finds no residual `{{...}}` token. |
| REQ-09 | Findings gate | Build per section 3. | `cls="bogus"` rejects; `cls="xxe"` accepts; `test_class_ext.py` stays green. |

REQ-09 follows REQ-32 as ruled, so it lands last in this group.

### Group 3 — verification and scoring

| Requirement | Target | Change | Acceptance test |
|-------------|--------|--------|-----------------|
| REQ-21 | `helpers/sec_overlay/verify.py` | Add a cause enum: `patch-not-applied`, `rule-no-match`, `unconfirmed`, `verified-static`. | Each cause is reachable and recorded. |
| REQ-22 | `helpers/sec_overlay/verify.py:169,316` | Resolve the rule source from the finding's own `rule_id`. Make the verdict independent of `drive(config=…)`. | The same finding yields the same verdict under two different `config` values. |
| REQ-06 | `agents/trace.md:15` | Widen the filter to `confirmed` and `needs-deployment-testing`. Require enumerating in-band reply-observable paths. | A `needs-deployment-testing` finding enters the trace phase. |
| REQ-20 | `helpers/sec_overlay/calibrate.py:91`; `references/prompt-constants.md:51-60` | Add `receipt_tier`, `verification`, and `reachability` terms. Make `_precondition_weight` the single source and regenerate the constants block from it. | C-SSRF-0001 outranks EXPR-EVAL-RCE-0001. |
| REQ-01 | `helpers/sec_overlay/patch_status.py:48-60` | Run the forward check first, returning `NOT_APPLIED` on return code 0. Then run the reverse check, returning `APPLIED` on return code 0. Otherwise return `UNKNOWN`. | A diff that applies cleanly forward reports `NOT_APPLIED`. |
| REQ-27 | `helpers/sec_overlay/models.py:154` | Collect unknown keys into `_overflow` and warn. Do not hard-fail. | An unknown key survives a load-and-save round trip. |

REQ-19 is the same change as REQ-06 and needs no separate commit.

### Group 4 — coverage and routing

| Requirement | Target | Change | Acceptance test |
|-------------|--------|--------|-----------------|
| REQ-04 | `helpers/sec_overlay/coverage.py:65,87`; `helpers/sec_overlay/report.py:426,590` | Remove the file-based `dataflow_pct` and `coverage.json`. Render from `coverage-ledger.json` only. | The report renders coverage with no `coverage.json` present. |
| REQ-11 | `helpers/sec_overlay/profile.py` | Add a `route_summary` field so `cls(**d)` stops raising. Derive it from `kb/route-census.json`. | A profile carrying `route_summary` loads. |
| REQ-25 | `helpers/sec_overlay/dependency_sinks.py:114` | In `reconcile_plan`, route a class on an indicator hit even with no manifest match. | A Bazel-style target holding `rego.New` and no `go.mod` routes `ssrf`. |
| REQ-24 | Investigate driver; `agents/investigate.md` | Wire `discovery_ledger.record_wave` (`discovery_ledger.py:41`) into the driver. Add wave language to the prompt. | A run records one wave per investigate wave. |

### Group 5 — render and terminal gate

| Requirement | Target | Change | Acceptance test |
|-------------|--------|--------|-----------------|
| REQ-03 | `helpers/sec_overlay/report.py:351` | Replace the hardcoded `"run redteam-plan test"` action. | The action text derives from the finding. |
| REQ-05 | `helpers/sec_overlay/report.py` | Omit empty measured sections. Suppress empty "No X" sections. Truncate titles on a word boundary. | A report with no measured data omits the section. |
| REQ-31 | New `helpers/sec_overlay/artifact_consistency.py` | Add a terminal gate after report and selfscore, before AUDIT COMPLETE. Implement checks (a) to (f). | A contradiction between two artifacts blocks the run. |

### Group 6 — capability lanes

| Requirement | Target | Change | Acceptance test |
|-------------|--------|--------|-----------------|
| REQ-33 | `references/finding.schema.json`; `helpers/sec_overlay/report.py` | Add the optional fields `attacker`, `privilege`, `exact_request`, `exfil_channels`, `refutation`, `library_version`, `negative_results`, and `baseline`. Render each as a section. | Each field renders when present and is omitted when absent. |
| REQ-34 | `helpers/sec_overlay/render_util.py`; `agents/redteam.md` | Accept `expected_signal` as a list of channels, each `{name, needs_egress, secure, insecure}`. Add a rule to enumerate the in-band channel first. | A list-valued `expected_signal` renders; the dict and bare-string forms stay green. |
| REQ-30 | Eight surfaces; see section 6 | Add the proof-by-execution lane. | Six tests; see section 6. |
| REQ-12 | `helpers/sec_overlay/ste_lint.py` | Reword the mandated front-matter sentence to pass the linter. Treat a wrapped list item as one logical line. Absorb the diagram-cap half of R-14. | The front-matter sentence passes; a wrapped list item does not trip the line rule. |
| REQ-14 | CodeQL Go autobuild | Write only under `.sec-overlay/`, or skip with the reason `codeql-go: build-unfenceable`. | A Go target with no fenceable build path records the skip reason. |

REQ-34 is additive, not a replacement. `render_util.signal_lines` is the single source of
truth for rendering `expected_signal`, and it currently accepts a dict, a bare string, or
`None`. Two green tests pin the bare-string form: `helpers/tests/test_report.py:631-644` and
`helpers/tests/test_redteam.py:73`. Read literally, the requirements document's "becomes a
list" would break both. Accept the list shape alongside the two existing shapes.

## 6. REQ-30 — proof by execution

REQ-30 reverses the harness invariant that the harness never executes the target. It is
opt-in and default off. Log the decision under `docs/decisions/`.

### Host

Add a new agent phase `prove` after `redteam` and before `artifact-gate`, near
`helpers/sec_overlay/phases.py:134`. Its prompt is `agents/prove.md`.

Do not attach the lane to `agents/verify.md`, which does not exist. Do not attach it to
`agents/redteam.md`, whose charter forbids execution. The phase must run after `redteam`,
because `redteam` sets the `needs-runtime` population the lane consumes.

### Flag

Gate the lane behind `scan_options.prove_findings`, a key inside the existing `scan_options`
dict at `profile.py:57`. Do not add a top-level `ScanProfile` field. `from_dict` is
`cls(**d)` at `profile.py:66`, so a top-level key raises.

### Population

Findings whose `runtime_disposition` is `needs-runtime`, plus `confirmed` findings whose
class is oracle-able.

### Soundness guard

Auto-confirm only on an entrypoint-driven end-to-end proof through the application's own
validation. That receipt records `scope: entrypoint`.

A slice-only proof records `scope: slice`. It never promotes. It attaches its harness and
stays `needs-runtime`.

### Class routing

Auto-confirmable classes: `ssrf`, `cmdi`, `path-traversal`, `deserialization`, and
`expr-eval-rce`. Route `sqli` and `authz` to a human-run harness. Their oracles are not
decidable by the wrapper without provisioning.

Class keys are the canonical keys of `references/attack-classes.md`. The Rego SSRF case is
class `ssrf`, per `attack-classes.md:37-38`.

### Execution fence

Build and run out-of-tree only. Never build in-tree, and never run the target's existing
tests in-tree. A `go build` writes `go.sum` and `go.mod`, which trips the working-tree fence
at `run.py:29`, called at `:224` and `:253`.

### Coded surfaces

1. `agents/prove.md`, the prompt.
2. A `PhaseSpec` in `phases.py`, after `redteam`.
3. `helpers/sec_overlay/prove.py`, the deterministic wrapper.
4. A loopback collector inside `prove.py`, built on `http.server` from the standard library.
5. Language toolchains in `preflight.py:25,41`, plus a persisted record. `prove.py` becomes
   the first consumer of `preflight_report` at `preflight.py:141`.
6. A `repro/` directory in `workspace.py:47-94`.
7. `"reproduction"` added to both `_MECHANICAL` and `TIER1_RECEIPTS` in `evidence.py:14,17`.
   Both edits land together, or the partition assert at `evidence.py:25` fails at import.
8. A `reproduction` payload object in `finding.schema.json`, holding `command`, `exit_code`,
   `oracle`, `oracle_result`, `toolchain`, `resolved_version`, and `scope`. Mirror it in
   `models.py`. The `evidence_sources` field is a bare string array, so the schema change is
   a payload object and not a receipt-type enum.

### Degradation

Record `prove: slice-unbuildable` or `prove: toolchain-absent`. A target that cannot build
degrades to today's behaviour, not to an error.

### Dependencies

The lane runs on darwin with no sandbox and no network namespace. It uses the standard
library and the tools already installed. Add no dependency.

### Acceptance tests

1. The lane is off by default.
2. An entrypoint proof promotes the finding and records `scope: entrypoint`.
3. A slice proof does not promote and records `scope: slice`.
4. A `sqli` finding routes to a human harness.
5. An absent toolchain records `prove: toolchain-absent` and does not error.
6. The reproduction receipt records the resolved toolchain version.

## 7. Deferred defects

Record these; do not fix them inside this requirement set.

- `class_extension_status` has no production caller. Only `helpers/tests/test_class_ext.py`
  imports it. Its docstring at `class_ext.py:1-5` promises gap recording, but nothing in the
  pipeline invokes it, so no gap is recorded today.
- `discovery_ledger.record_wave` at `discovery_ledger.py:41` has the same shape. REQ-24
  wires it in, which closes this one.

## 8. Verification gates

- Run the full plugin test suite after each group. The baseline is 1619 tests passing.
- REQ-32 and REQ-31 must run in the pipeline and must block on drift or on an artifact
  contradiction. Prove each with its acceptance test.
- After the capability lanes land, re-run sec-overlay against the Rego target at
  `/Users/christopher/Workspace/review_enforce/enforce`. Confirm that the finding page
  carries the eight Part D elements, that the red-team directive lists the no-egress in-band
  oracle first, and that the reproduction receipt records the OPA version.

## 9. Commit protocol

- One requirement per red-green pair. The red commit adds the failing acceptance test. The
  green commit adds the code. A single commit holding both skips the red phase.
- Carry the requirement id in both subjects, matching the established pattern.
- Stage explicit paths only. Never bypass the hooks.
- Bump the plugin version in `plugins/sec-overlay/.claude-plugin/plugin.json` in the same
  commit as any shipping-file change. A breaking change bumps major, `feat` bumps minor, and
  every other type bumps patch.
- Stage the touched folder's `README.md` in the same commit.
- Run `prek run` before each commit.

## 10. Definition of done

- All 29 requirements land, each with a passing acceptance test.
- The full suite passes at the end of every group.
- REQ-31 and REQ-32 block in the pipeline.
- Each capability lane sits behind a flag, and a target lacking the needed input degrades to
  today's behaviour.
- The Rego re-run confirms the eight Part D elements.
- The REQ-30 decision is logged under `docs/decisions/`.
</content>
