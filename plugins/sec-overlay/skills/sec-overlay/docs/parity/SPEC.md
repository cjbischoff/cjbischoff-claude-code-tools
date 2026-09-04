# SPEC — OCR parity and benchmark superiority for sec-overlay

Date: 2026-08-23. Source inventory: `EXTRACTION.md` (same folder). Every inventory row maps
to a requirement id below or carries a written disposition. No third state exists.

Ordering law (from THE ANALYSIS Part 6/7): measurement before parity. Milestone 1 blocks
Milestones 2–4, because no later item may land without a before/after benchmark delta.

Binding constraints C1–C8: see EXTRACTION.md "Binding constraints". They apply to every
requirement and are not repeated per row.

---

## Milestone 1 — Measurement foundation

### REQ-M1 — F1 in the scorecard (EXTRACTION M1)
Add `f1` to every metrics dict in `bench/tally.py` (`_metrics`), to `Scorecard.to_dict`,
and to `to_markdown`. Formula: `2*P*R/(P+R)`; `None` when P or R is `None` or `P+R == 0`.
**Acceptance:** a test feeds known tp/fn/fp and asserts the exact F1 value; a test asserts
`None` on the zero branch; markdown output shows an F1 line.

### REQ-P9 — judge severity write-back (EXTRACTION P9, W5d)
When `judge_verdict` in `("severity-inflated", "downgrade")`, calibrate writes the derived
(post-downgrade) severity back to `f.severity`, appends a history event
`calibrate:severity-downgraded` recording `from`/`to`, and keeps the existing risk_score
logic. Derived severity comes from a documented risk_score→severity band map (new module or
function; `models.py` is frozen — write-back uses the existing mutable field, no schema
change). **Acceptance:** RED test — a finding with inflated severity + downgrade verdict
renders the lowered severity in `report.md` and `findings/*.json`; history carries the event;
a no-verdict finding is untouched.

### REQ-M2 — headless skill driver (EXTRACTION M2)
Implement `CCSkillAdapter.scan()` in `bench/adapter.py` (or a new `bench/driver.py` it
delegates to) as a subprocess driver: invoke `claude -p` (configurable binary + args) with a
per-entry prompt that runs the review/scan flow into a workspace, then grade via the existing
`WorkspaceAdapter`. Resumable: per-entry cache keyed by entry id + target sha; a completed
entry is never re-run. Failure = record `{entry, error}` and skip — never fabricate findings.
Stdlib-only; the `claude` binary is shelled like a SAST tool. **Acceptance:** unit tests with
a fake runner assert command construction, cache hit/miss, failure recording; no network in
tests.

### REQ-M4 — corpus ≥30 entries (EXTRACTION M4) + CI gate (M4a)
Grow `bench/corpus_seed/` to ≥30 entries across: locked positives from prior confirmed
findings (fixture-backed where private), negatives from correctly-rejected leads, ≥3
dep-CVE entries, ≥5 public-app entries (OWASP Juice Shop / WebGoat pinned commits, entries
reference the pinned commit — repos fetched at run time, never vendored). Every entry loads
through `corpus.py` validation. Add a GitHub workflow running `pytest` + `bench.run` against
the deterministic (workspace/fixture) adapter; exit 1 on locked-miss fails CI.
**Acceptance:** `corpus.py` load test counts ≥30 and validates kinds/sources; workflow file
exists and runs the gate; a synthetic locked-miss test proves exit 1.

### REQ-M3 — AACR adapter + published judge (EXTRACTION M3, M3a–M3d)
1. **M3d first:** inspect `Alibaba-Aone/aacr-bench` (Hugging Face). Record its real schema in
   `bench/README.md`. If the dataset is unreachable in this environment, the adapter is built
   against the documented row shape from the dataset card and marked `untested against live
   data` — never guessed silently.
2. `bench/aacr_adapter.py`: AACR row → `CorpusEntry`, `source="aacr"`, never blended into the
   `real-confirmed` headline (tally already segments by source; add a guard test).
3. Runner mode that grades OCR's own `ocr review --format json` output under the identical
   `judge.py` criterion, producing one table: tool × {F1, P, R, FP-rate, wall-time}.
4. Scorecard text states: the matching rule (class + file + line ≤ 12 + fingerprint;
   CVE-match for deps) and the caveat that cross-tool numbers are comparable only under the
   same judge. Any LLM judge prompt is a versioned artifact.
**Acceptance:** adapter unit tests on fixture rows; a tally test proving `aacr` never enters
the headline; scorecard markdown contains the judge statement and caveat.

### REQ-M5 — variance (EXTRACTION M5, R5, T3f)
`bench/run.py` supports `--repeats N` (default 1); the scorecard aggregates per-config mean ±
range (min/max) for P/R/F1/FP-rate. **Acceptance:** test with 3 synthetic runs asserts mean
and range in `to_dict` and markdown.

### REQ-M6 — latency column (EXTRACTION M6, T3b partial)
The run record carries per-entry wall-time, from the adapter's own timing. The scorecard emits
wall-time. It emits no token count and no `$ / confirmed-TP` column, because REQ-46 deleted the
token and cost measurements from `cost.py`. FP-rate is published per class (T3b).
**Acceptance:** tests over synthetic run records assert the wall-time column and the per-class
FP-rate rows.

### REQ-R3 — annotation protocol statement (EXTRACTION R3)
`bench/README.md` documents how internal corpus entries are labeled, who adjudicates
(single-maintainer adjudication stated plainly), and how disagreements with the judge are
recorded. No invented statistics. **Acceptance:** section exists; `test_docs_invariants`-style
assertion pins its presence.

### REQ-R1/R4 — reproducibility + confound statement (EXTRACTION R1, R4, M3c, HR3)
One documented command reproduces the benchmark end to end. The scorecard states the scope
confound (deterministic file selection reviews less; token gap partly measures "doing
less"). OCR is graded under the same judge (REQ-M3.3); losses it reports are accepted and
published unedited. **Acceptance:** README run command; scorecard contains the confound
statement.

## Milestone 2 — Review-mode parity

### REQ-P6 — wire live reflection (EXTRACTION P6)
Replace the literal `{}` at `cli.py:553`: prepare renders the existing
`agents/review-filter.md` prompt per file (or unit) over the kept findings; dispatch stays in
`SKILL.md` (D-13 — the Python core never calls an LLM); consume reads the recorded verdict
from the workspace (`read_agent_return`) and feeds it to `apply_verdict`. A missing/unparsable
verdict is a fail-open `ReflectionSkip`, recorded in the ledger. `PROTECTED_SUBJECT_CLASSES`
semantics unchanged. **Acceptance:** RED test — a recorded verdict retracts a non-protected
finding and cannot retract a protected one; a missing verdict yields a `ReflectionSkip` entry
in `review_ledger.json`.

### REQ-P1 — sibling-diff visibility + richer bundling (EXTRACTION P1a, P1b, D8, V1)
(a) The review prompt for a multi-file `ReviewUnit` includes each member's diff, and the
changed-files block for every file annotates unit membership; single-file units keep listing
sibling paths and additionally include sibling diffs up to a size cap (token-estimated,
REQ-P4 estimator), largest-first truncation with an explicit `omitted` marker.
(b) Extend `bundle.py` grouping: header/impl pairs (`.h/.c`, `.hpp/.cpp`), interface/impl
(`foo.ts`/`foo.impl.ts` style stem pairs), and import-adjacency from `kb/graph.json` when a
graph exists (optional input — review mode must not require an audit-phase artifact). Cap
bundle token size; overflow splits the unit. Never describe this as porting OCR bundling
(OCR's review-mode bundling does not exist — refuted claim V1).
**Acceptance:** RED tests — prompt contains sibling diff text; oversized sibling content
truncates with marker; new pair rules group correctly; token cap splits.

### REQ-P2 — rule docs 9 → 36 (EXTRACTION P2, W7)
Port the remaining OCR rule docs in the analysis priority order (terraform, yaml,
github_workflows, github_config, package_json, cargo_toml, pom_xml, composer_json,
build_gradle, c, cpp, protobuf, graphql, prisma, json, properties, nix, bicep, then the
rest), each with: Apache-2.0 attribution header naming OCR, sec-overlay's exclusion-block
format, and a `BUILTIN_PATH_RULE_MAP` glob added in the same commit (map order = match
order). **Acceptance:** a test asserts doc count, per-file attribution line, and that every
map entry resolves to an existing doc (extend the existing rule_glob tests).

### REQ-P4 — hard token budget + token-aware file guard (EXTRACTION P4, P4a, D1, D4, D5, D10)
New module `review_budget.py` (models frozen — new module): `estimate_tokens(diff_text)`
using OCR's shape (`diff/4 + prompt overhead + rounds×(diff+overhead) + rounds×output`,
constants documented and asserted in `test_docs_invariants.py`). `cli.py review
--token-budget N` (0/absent = unlimited): look-ahead gate before scheduling a unit — on
projected breach stop scheduling, let in-flight finish, mark remaining files `failed` with
note `skipped(budget)` in the coverage manifest (manifest vocabulary unchanged — the note
carries the class, mirroring OCR's failure-class vocabulary D4), surface
`budget_exceeded: true` in `review_result.json` and the ledger, seal `partial`, exit 0 (D5:
partial coverage is a controlled outcome). Per-file token-aware guard (P4a): a file whose
estimate alone exceeds the budget fraction cap is excluded with the existing `too-large`
reason extended by a token variant. `--prepare` output gains a per-file token estimate (D10).
Audit-mode `token_budget` stays soft — no change there. **Acceptance:** RED tests — estimator
constants; gate stops scheduling at the boundary; manifest note; exit code 0 with
budget_exceeded flag; prepare emits estimates.

### REQ-P5 — review input modes (EXTRACTION P5)
`cli.py review --commit <sha>` (reviews that commit: base = `sha^`, head = `sha`) and
`--workspace-dirty` (staged + unstaged + untracked vs HEAD; untracked files appear as
added-file diffs). Mutually exclusive with `--base/--head`; ref validation through the
existing `diffscope.validate_ref` path; resume identity records the mode.
**Acceptance:** RED tests over a fixture repo — commit mode picks the right parent; dirty
mode sees staged, unstaged, and untracked changes; flag conflicts exit 2.

### REQ-P3 — per-file plan phase (EXTRACTION P3, D3)
Optional `--plan` step in review prepare: files (units) whose diff line count ≥ a documented
threshold (default from OCR's shape, D3) get a plan prompt rendered from a new
`agents/review-plan.md`; the recorded plan JSON (strict schema: `issues[]` with severity
ordering + per-issue guidance) is injected into the review-file prompt as a
`{{PLAN_GUIDANCE}}` token; below threshold, skipped. Dispatch stays in `SKILL.md` (D-13).
Fail-open: a missing/invalid plan return renders the review prompt without guidance and
records the skip. **Acceptance:** RED tests — threshold skip; injection; fail-open.

### REQ-P7 — consolidated `review_result.json` (EXTRACTION P7)
One artifact written last in consume: status, per-finding records (id, path, line, severity,
rule_id, profile, disposition), dropped/declined, reflection retractions/skips,
budget_exceeded, coverage manifest, per-phase token records, base/head SHAs, model/profile.
Existing artifacts stay (additive). **Acceptance:** RED test — file exists with all keys on a
zero-finding run and on a populated run; keys match the documented contract.

### REQ-P8 — background context (EXTRACTION P8)
`--background <text>` / `--background-file <path>`: 1 MB cap, control-character strip,
delimiter-smuggle guard (strip/escape the envelope nonce delimiters), then
`redactor.safe_for_prompt`, then included in the review prompt inside the trust envelope.
**Acceptance:** RED tests — cap enforced (exit 2), control chars stripped, a secret in
background text aborts via `SecretsPresent`, prompt contains the enveloped text.

## Milestone 3 — Shell + credibility

### REQ-S1 — GitHub Action + comment poster (EXTRACTION S1, D9)
`action.yml` at the plugin (or repo) level: runs review mode headless (REQ-M2 driver),
uploads SARIF to code scanning, posts PR comments from `review_result.json` — severity
routes inline-vs-summary (D9 parity), event `COMMENT`. Poster is a stdlib Python script (no
Node dependency). **Acceptance:** unit tests for the poster's routing/payload construction
with a fake GitHub API; action.yml lints (actionlint).

### REQ-S3 — `ASSURANCE_CASE.md` (EXTRACTION S3, D7, G-advantage rows)
Written to `skills/sec-overlay/ASSURANCE_CASE.md`, OCR's shape: actors, trust boundaries
(repo text → prompts: envelope + redactor with file:line; subagent writes: write-guard;
target never executed/modified: verify.py copy discipline), threats, Saltzer–Schroeder +
OWASP/CWE mapping, automated checks (pytest, ruff, ty, docs-invariants, prek). States the
OCR contrast honestly (OCR sends diffs unredacted, D7) without marketing language.
**Acceptance:** STE100-lint clean (`ste_lint`); every countermeasure cites an existing
file:line that resolves (test walks the citations).

### REQ-S2 — sessions list/show (EXTRACTION S2, X3)
`cli.py sessions list --target <T>` (one row per sidecar run: pass, sha, date, finding
counts) and `sessions show <id|latest>` (statuses, phases, review ledger summary; severity
filter covers X3's scope). Read-only over existing state/ledger files. **Acceptance:** RED
tests over a fixture workspace.

### REQ-S4 — did-you-mean + rules check (EXTRACTION S4)
`cli.py rules check <path>` prints the resolved rule doc + layer (rule_glob resolver).
Unknown subcommand/flag suggestions via `difflib.get_close_matches` on argparse error.
**Acceptance:** RED tests — resolver output; a misspelled subcommand's error names the
nearest valid one.

## Milestone 4 — Press the advantage

### REQ-T3a — fast review tier (EXTRACTION T3a, G2, HR2)
`--tier fast|assured` (default assured) on review: fast = position gate + reflection +
receipt/profile gates only (skips plan and any critic/validate-style steps); assured = full
chain. Tier recorded in manifest + result JSON, so benchmark rows are labeled.
**Acceptance:** RED test — fast tier's consume path skips the heavy steps and records the
tier.

### REQ-T3c/T3h — verified-fix rate (EXTRACTION T3c, T3h)
Scorecard adds `verified_fix_rate` = `fixed ∪ verified-static` / confirmed, when a run
provides fix data; headline table renders the count. **Acceptance:** synthetic-run test.

### REQ-T3d — coverage-honesty audit (EXTRACTION T3d)
Scorecard adds unsupported-coverage-claim rate: entries whose run claimed `complete` while
the ledger held open surfaces (machine-derivable from `coverage-ledger.json`).
**Acceptance:** synthetic-run test with one honest and one dishonest ledger.

### REQ-T3e — security slice (EXTRACTION T3e, R7)
`aacr_adapter` tags security-category rows; tally emits an `aacr-security` slice. Depends on
M3d dataset inspection for the category field. **Acceptance:** fixture-row test.

---

## Dispositions (inventory rows with no requirement)

| Row | Disposition |
|-----|-------------|
| G18 (terminal UX, viewer TUI, VS Code ext) | rejected: sec-overlay's interface is the Claude Code conversation plus `report.md`/SARIF; a TUI or editor extension is a separate product with zero benchmark effect; THE ANALYSIS assigns it no tier. |
| G19 (multi-provider) | rejected: THE ANALYSIS marks it "n/a by design — skip"; the host harness owns providers. |
| G20 (delegation mode) | rejected: THE ANALYSIS — "low value; its whole product is the delegate". |
| G21 (deliberate MCP routing) | deferred: host Claude Code already exposes MCP tools to subagents; deliberate routing is a prompt-design change with no measured benefit; revisit after the first benchmark run exists. Recorded here. |
| D6 (cross-comment dedup in review mode) | deferred: per-unit parse already anchors findings to member files; cross-file duplicates in a single diff are rare and `dedupe.py` exists for audit mode; add only if the first benchmark shows duplicate-driven precision loss. Recorded here. |
| X1 (mid-loop memory compression) | rejected: the Claude Code harness owns subagent context management; the Python core never holds an LLM conversation. |
| X2 (retry layers + retry report) | rejected: the harness owns retries; `SKILL.md` wave dispatch (3–4) is the provider-load mitigation; a retry report has no enforcement point in a harness-orchestrated skill. |
| X4 (non-GitHub CI recipes) | deferred: SARIF output is CI-agnostic; document generic SARIF upload in README; per-vendor recipes have no benchmark effect. Recorded here. |
| X5/X6 (npm distribution, provider wizard, `llm test`) | rejected: folded into G18/G19 — distribution is the plugin marketplace; providers are the host's. |
| X7/X8, G13, G14–16/23–27/30/33/34, V4 | context rows: no work; X7 and the win rows feed the comparison table narrative; X8 never cited as benchmark. |
| T3g (score-vs-human-triage agreement) | deferred: THE ANALYSIS conditions it on "once corpus exists" with human triage labels; the ≥30-entry corpus (REQ-M4) lacks independent human triage today. Recorded here. |
| W5a/W5b/W5c, W5e, D2, R6 | already-done: evidence in EXTRACTION.md; no work. |
| W6 | already-managed: `test_docs_invariants.py` discipline continues as constraint C5. |
| D1, D3, D4, D5, D9, D10, V1–V3, V5–V7, HR1–HR3 | spec inputs: folded into the requirements named on their EXTRACTION rows. |

## Execution caveat (honest scope statement)

Machinery (code, tests, corpus, adapters, action, docs) is implementable and verifiable in
this session. Full AACR-scale benchmark executions (200 PRs × ≥3 repeats × two tools) burn
real LLM quota and hours of wall time; the spec requires the machinery and a documented
one-command run, and the plan schedules a smoke-scale run. The full published table is an
operator-executed step; its absence in this session is recorded in PARITY-AUDIT.md as
deferred-execution, not silently dropped.

## Traceability matrix

| EXTRACTION row | Requirement / disposition |
|----------------|---------------------------|
| M1 | REQ-M1 |
| M2 | REQ-M2 |
| M3, M3a, M3b, M3c, M3d | REQ-M3 |
| M4, M4a | REQ-M4 |
| M5 | REQ-M5 |
| M6 | REQ-M6 |
| P1a, P1b | REQ-P1 |
| P2 | REQ-P2 |
| P3 | REQ-P3 |
| P4, P4a | REQ-P4 |
| P5 | REQ-P5 |
| P6 | REQ-P6 |
| P7 | REQ-P7 |
| P8 | REQ-P8 |
| P9 | REQ-P9 |
| S1 | REQ-S1 |
| S2 | REQ-S2 |
| S3 | REQ-S3 |
| S4 | REQ-S4 |
| T3a | REQ-T3a |
| T3b | REQ-M6 (per-class FP-rate) |
| T3c, T3h | REQ-T3c/T3h |
| T3d | REQ-T3d |
| T3e | REQ-T3e |
| T3f | REQ-M5 |
| T3g | disposition: deferred |
| R1 | REQ-R1/R4 |
| R2 | REQ-M3 (judge publishing) |
| R3 | REQ-R3 |
| R4 | REQ-R1/R4 |
| R5 | REQ-M5 |
| R6 | already-done |
| R7 | REQ-T3e |
| W1–W7 | mapped per EXTRACTION (M4, M2, M1, P6, W5a–e dispositions/already-done, C5, P2) |
| G1, G3, G6, G12, G17, G22, G28, G29, G31, G32 | REQ-P5, REQ-P4, REQ-P3, REQ-P4, REQ-P7, REQ-S1, REQ-S3, REQ-M3/M4, REQ-P8, REQ-S4 |
| G2 | REQ-T3a |
| G13, G14–16/23–27/30/33/34 | context |
| G18, G19, G20, G21 | dispositions above |
| D1–D10 | spec inputs / dispositions above (D2 already-done, D6 deferred, D7 → REQ-S3) |
| X1–X8 | dispositions above (X3 → REQ-S2) |
| V1–V7 | spec guards / context per EXTRACTION |
| HR1–HR3 | encoded in REQ-M3, REQ-T3a, REQ-R1/R4 + plan ordering |
| C1–C8 | binding constraints on all work |
