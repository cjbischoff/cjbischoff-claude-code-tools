# sec-overlay Defect Report — Missed Authenticated RCE in Tanium Comply

**Date:** 2026-09-02
**Harness:** `sec-overlay` plugin (audit run under 1.107.3; code cited from 1.122.0 unless noted)
**Run:** 4-member audit — `comply`, `go/cmd/goval-cli`, `go/internal/enrichmentlibrarybuilder`, `go/internal/xccdf`; pinned SHAs `a398fceee3da` (comply), `550e194eae16` (go)
**Reference finding:** `render-output-injection-01` — uploaded OVAL XML reaches `new Function` via `dot.template`, RCE as the Comply service identity on the Tanium Module Server (independent audit, verdict confirmed, reproduced)
**Verdict:** the harness did not find this finding, and could not have confirmed it as currently built. Nine independent defects each block it. Five of them cause silent loss — no gap row, no ledger entry, no id.

---

## 0. Scope of this report

This is a defect report against the harness, not against Comply. It answers one question: with the same source tree, the same pinned SHAs, and the run's own artifacts on disk, why did this finding not appear, and which harness behaviors have to change so that it would.

Every claim below cites either plugin source (`file:line`) or a run artifact under a `.sec-overlay/` sidecar. Where the audited run used plugin 1.107.3 and the citation is from 1.122.0, the 1.107.3 equivalence is stated explicitly.

Terminology: **class** = attack-class key routing a candidate to an investigate agent; **receipt** = a mechanical `evidence_sources` entry `evidence.is_tool_receipt` accepts; **member** = one repo/scope in the correlation manifest.

---

## 1. The finding, reduced to its dataflow

```
POST /v1/vulnerability-sources          (openapi/paths/internal/vulnSource.v1.yaml:29)
  → VulnSourceService.processCustomSourceFiles     (src/service/services/VulnSourceService.ts:1149)
  → goval-cli import                                (external process, Go)
  → ParseOVAL captures raw root-element bytes       (internal/.../oval/parser.go:112)
  → insertOvalSource stores them verbatim           (internal/.../oval/vulndb.go:1073)
  ══ DB column sources.feed_template ══             (cross-process, cross-language, cross-member)
  → NormalIntelFeedWriter.writeOvalChunk            (src/service/__new__/src/vulnerability-source/intel-file-writers/normal.ts:69-70)
  → templates.build(templateHeaderText)             (src/service/__new__/src/util/templates.ts:93-95)
  → dot.template(template)                          → new Function(varname, str)   [inside node_modules/dot@1.1.3]
```

Three properties of this shape matter for every defect below:

1. **The sink is dependency-internal.** `new Function` is inside the `dot` package. First-party code stops at `dot.template(template)` (`templates.ts:94`).
2. **The taint channel is a database column**, crossing a process, a language, and two audit members.
3. **The class is code-injection / template-injection**, not any class the run planned.

**The run had the evidence available.** Verified on the audited tree at the pinned SHA:
- `src/service/__new__/src/vulnerability-source/intel-file-writers/normal.ts:69-70` — sink call present.
- `src/service/__new__/src/util/templates.ts:93-95` — `export function build(template) { return dot.template(template); }` present.
- `src/service/package.json:127` — `"dot": "1.1.3"` declared.
- `node_modules/` is **not** installed anywhere in the tree (`src/service/node_modules/dot` absent). The `new Function` line was physically unavailable to any scanner.

**What the run produced at those files instead:** `normal.ts` — no finding of any status. `intel-file-writers/bzipped.ts:27,28`, `cached-intel-db.ts:334`, `feeds.ts:212` — semgrep `path-join-resolve-traversal` hits only, all `rejected`. `VulnSourceService.ts` — 15 `rejected` path-traversal candidates plus `SSRF-0001` (needs-deployment-testing) at line 851 on `remote_file` URL re-resolution, i.e. a different parameter of the same service. Zero findings in any of the four members carry class `ssti`, `expr-eval-rce`, `injection`, `code-injection`, or `deserialization`.

---

## 2. Defects

Ordered by how early they cut the finding off. Each has: evidence, root cause, required behavior, acceptance test.

### D-1 — CWE-94/CWE-95 are absent from the class map, so every eval/code-injection rule hit resolves to `unknown`

**Evidence.** `helpers/sec_overlay/clsmap.py:17-30` — `CWE_CLS` maps 24 CWEs. CWE-94 (Code Injection) and CWE-95 (Eval Injection) are not among them. Identical in 1.107.3 (`clsmap.py:18`). The two vendored semgrep rules that carry the right sink pattern both declare CWE-95 and nothing else the map can use:
- `rules/semgrep/javascript/lang/security/detect-eval-with-expression.yaml` — `cwe: ["CWE-95: ... ('Eval Injection')"]`, sinks include `new Function(<... $SINK ...>)`, severity `WARNING`.
- `rules/semgrep/javascript/lang/security/audit/code-string-concat.yaml` — `cwe: ["CWE-95: ..."]`.

`cls_from_semgrep_meta` (`clsmap.py:131-163`) resolves in order `cls` → mapped `cwe` → `cls_from_rule_id` → `security-other`/`unknown`. Neither rule id contains any substring in `_RULE_ID_CLS` (`clsmap.py:38-68`: `exec-use`, `backticks-use`, `weak-crypto`, `tainted-path`, `redos`, …). Result: `cls = "unknown"`.

**Root cause.** The CWE table is hand-maintained and omits the entire dynamic-code-execution family. The rule-id fallback list was curated for path/crypto/redos rules and never extended to eval.

**Required behavior.** `CWE_CLS` must map CWE-94, CWE-95, CWE-1336 (already present), and CWE-471/CWE-913-family template/code-eval CWEs to a routable class. A class key must exist for raw dynamic execution: `agents/classes/injection.md` exists and `ssti.md:28-30` explicitly instructs investigators to file raw `eval`/`exec` as `cls: injection`, but **no CWE and no rule-id entry ever routes anything to `injection`** — the class is reachable only by an agent's free choice, never deterministically. That is a taxonomy break, not a gap.

**Acceptance test.** A semgrep result whose metadata is `{"cwe": ["CWE-95: ..."]}` and whose `check_id` is `detect-eval-with-expression` must resolve to a class in `canonical_classes()` that has a class prompt, and must appear in `agents_to_spawn` after `reconcile_plan`.

---

### D-2 — `security_only` deletes every `unknown`-class semgrep finding before any triage, keeping only an integer

**Evidence.** `helpers/sec_overlay/prefilter.py:289-296`:

```python
security_only = sem.get("security_only", True)
if security_only:
    def _is_semgrep(f): return any(s.startswith("semgrep:") for s in f.evidence_sources)
    before = len(raw)
    raw = [f for f in raw if not (_is_semgrep(f) and f.cls == "unknown")]
    dropped_nonsecurity = before - len(raw)
```

Default on. The filter is unconditional on severity. Combined with D-1, a CWE-95 `new Function` taint hit is deleted at prefilter with **no finding id, no file, no line** — only the count `dropped_nonsecurity`.

**Consequence, and it is worse than it looks.** `partition.demote_noise` (`partition.py`, `demote_noise`) contains a rescue branch:

```python
if f.cls == "unknown" and f.severity in (Severity.HIGH, Severity.CRITICAL):
    f.cls = "security-other"; f.history.append({"event": "partition:reroute-high-sev-unknown"})
```

That branch is **dead code for semgrep findings** — `run_prefilter` already deleted them. The harness's own safety net for unmapped-CWE hits cannot fire on the backend that produces most of them.

**Root cause.** A noise-reduction filter keyed on the *classifier's failure* (`cls == "unknown"`) rather than on the *rule's own security metadata* (`metadata.category == "security"`, `subcategory: vuln`, CWE present). A rule that declares a CWE and `category: security` is being treated as non-security lint because the harness could not map its CWE.

**Required behavior.** Never drop a semgrep result that declares `category: security` or any `cwe` field. Route unmapped-but-security-declared hits to `security-other` (the general-triage lane already exists and ran in this audit). Any drop must be recorded per finding — id, file, line, rule id, reason — in a persisted drop ledger, not aggregated into a count.

**Acceptance test.** Run the prefilter over a fixture containing one CWE-95 `new Function` hit. Assert: the finding survives with class `security-other` or better; if any policy drops it, `kb/<drop-ledger>.json` names it with file:line and reason.

---

### D-3 — The dependency-sink catalog has no JavaScript/npm entries, so the one mechanism built for dependency-internal sinks cannot fire on a Node target

**Evidence.** `references/dependency-sinks.json` holds 6 entries: 5 `ecosystem: "go"`, 1 `"python"`. Zero npm. Identical in 1.107.3. The catalog's declared purpose (`partition.reconcile_plan` docstring, `partition.py`) is exactly this finding's shape:

> "A dependency can hold the sink inside its own code (an OPA policy calling `http.send`), which leaves no first-party pattern for recon to see."

`reconcile_plan` merges `matched_classes(target_root) + indicator_classes(target_root)` (`partition.py`). `dependency_sinks.match_manifests` matches package names inside manifest filenames the entry names (`dependency_sinks.py:158-184`); entries name `go.mod`/`go.sum`/`requirements.txt` only. `_SOURCE_SUFFIXES` (`dependency_sinks.py:~120`) does include `.js`/`.ts`, so indicator matching would work — there is simply nothing to match.

`dot@1.1.3` is declared at `src/service/package.json:127`. A catalog entry of the form `{package: "dot", ecosystem: "npm", manifests: ["package.json", "package-lock.json"], cls: "ssti", sink: "dot.template → new Function", indicators: ["dot.template", "doT.template", "require('dot')"]}` would have added `ssti` to `agents_to_spawn` deterministically, with no recon judgment involved.

**Root cause.** Catalog content coverage. The mechanism is correct and the wiring is correct; the data covers one ecosystem family and the audited target is in another.

**Required behavior.** The catalog needs npm coverage for template/eval-compiling packages at minimum: `dot`, `ejs`, `pug`, `handlebars` (compile with `noEscape`), `lodash.template`, `vm2`, `serialize-javascript`, `eval`, `safe-eval`. Manifest names must include `package.json` and `package-lock.json`. Catalog coverage per ecosystem present in any scanned target should itself be a preflight-reported metric — a Node target scanned with zero npm catalog entries is a known blind spot and should be logged as one.

**Acceptance test.** `reconcile_plan(ws, ["xss"], target_root=<comply>)` must return a list containing a template-injection class, on the strength of `package.json:127` alone, with no candidate findings present.

---

### D-4 — Uninstalled `node_modules` plus the tool-receipt gate make a dependency-internal sink unconfirmable even when an agent reasons it out correctly

**Evidence.** The audited tree has no `node_modules` installed. `route_census._SKIP` (`route_census.py:20`) excludes `node_modules/*`; `dependency_sinks._manifest_files` skips vendored and cache trees. So the `new Function` line is invisible to semgrep, to CodeQL (`sast_plan.codeql.languages = ["javascript"]`, suite `security-extended`), and to `ast-grep`.

The confirmation gate is absolute: `findings_gate.py:50-58` requires at least one `evidence_sources` entry accepted by `evidence.is_tool_receipt()`; the mechanical whitelist (`evidence.py` `_MECHANICAL`) is `semgrep`, `codeql`, `ast-grep`, `tree-sitter`, `ripgrep`, `structural-index`, `secrets`, `sca`. `SKILL.md` states the rule plainly: "A finding with only `llm-claimed:*` evidence sources cannot reach `confirmed`."

**This is the mechanism by which the harness "gives up" on a correct finding.** An investigate agent that read `normal.ts:69`, `templates.ts:94`, and `package.json:127` and correctly concluded RCE could cite `ripgrep`/`structural-index` receipts for the first-party call chain — but the receipt for *"`dot.template` is `new Function`"* does not exist in the tree, so the decisive hop is `llm-claimed:*`. Best case the finding stalls at `needs-deployment-testing`; worst case validate rejects it for missing sink evidence. The competing audit resolved this by **executing** the path (built goval-cli, ran the import, compiled the recovered bytes through the installed `dot@1.1.3`, executed OS commands). sec-overlay has no equivalent lane on by default — see D-8.

**Root cause.** The receipt whitelist recognizes only receipts obtainable from *first-party source in the tree*. There is no receipt kind for "this dependency version's implementation of this API is a code-execution sink", even though `references/dependency-sinks.json` exists precisely to encode that knowledge. Note `ssti.md:38-41` already anticipates the need — it describes a `dependency-catalog:<id>` receipt that "names a dependency-internal render call when the sink has no first-party line" — but `dependency-catalog` is **not** in `evidence.py`'s `_MECHANICAL` set, so the prompt promises a receipt the gate refuses.

**Required behavior.** Either (a) add `dependency-catalog:<entry-id>` to the mechanical receipt set, pinned to a resolved version from the lockfile so the claim is falsifiable, and require the catalog entry to cite the sink API and the version range; or (b) make the harness resolve dependency source before scanning (install, or fetch the package tarball read-only into a scratch tree and scan that), so a real `semgrep`/`ast-grep` receipt on the dependency's own line becomes obtainable. (a) is cheaper and matches the existing prompt contract; (b) is stronger. Whichever is chosen, the prompt text and the gate must agree — today they contradict each other.

**Acceptance test.** A finding whose chain is `first-party call → catalogued dependency sink`, carrying `dependency-catalog:npm-dot-template` plus a lockfile-pinned version, must be able to reach `confirmed`. Conversely a `dependency-catalog` receipt naming a version outside the entry's declared range must be refused.

---

### D-5 — The coverage ledger is derived from recon's own attack surface, so a class recon never named cannot appear as a gap

**Evidence.** Run artifact `kb/scan-profile.json` — `attack_surface` = `[xxe, path-traversal, fileupload, sqli, cmdi, ssrf, secrets, crypto, xss, authz, deps, prompt-injection]`. No `ssti`, `expr-eval-rce`, or `injection`. `agents_to_spawn` is the same list minus `deps`; `runs/investigate.txt` records "14 investigate class agents completed (…)" — the planned set plus `open-redirect`, `resource`, `security-other`.

`coverage_ledger.build_coverage_ledger` computes the ledger from `attack_surface × finding status` (documented in `SKILL.md` step 14 and `CLAUDE.md` §4). The run's `kb/coverage-ledger.json` lists exactly 11 surfaces, every one `needs_follow_up`, and `completeness: "partial"`. The report renders that table (`report.md:213+`).

So the ledger is a closed loop: recon proposes the surface, the ledger grades the surface recon proposed. A missing *class* is structurally invisible; only a missing *finding within a named class* can register. `recall-gate` does not close this — it recomputes the route census and the dependency-catalog classes only (`driver._act_recall_gate`, `route_control.record_route_gaps`), and it passed with zero errors: `kb/gates/recall-gate.json` = `{"passed": true, "errors": [], "warnings": []}`.

**Root cause.** No mandatory class floor. Nothing asserts "for a Node/TypeScript target, the following classes must be either investigated or explicitly excluded with a reason".

**Required behavior.** A language/framework-derived **mandatory class floor**, independent of recon's judgment: for a JS/TS target, template-injection and dynamic-code-eval are on the floor. Every floor class must terminate in one of two states — investigated (with a finding, including a "no instance found" terminal) or excluded with a cited reason. A floor class that is neither must force `completeness: partial` **and** name the class in the ledger. Recon may add to the surface; it may not shrink below the floor.

**Acceptance test.** Delete `xss` from a fixture profile's `attack_surface` for a TS target. The ledger must contain an `xss` row with disposition `needs_follow_up` and reason "mandatory floor class not investigated", and `completeness` must not be `complete`.

---

### D-6 — The route census cannot see OpenAPI-registered routes, and its output is dominated by test files and non-routes

**Evidence.** `references/route-frameworks.json` defines 7 frameworks — flask, fastapi, django-urls, go-nethttp, go-chi-gin-echo, express, spring. All are regex-over-source (`route_census._rg`, `route_census.py:72-86`). None models an OpenAPI/`operationId`-registered route. Comply registers its internal routes exactly that way — `AGENTS.md`: routes are "defined in the internal OpenAPI spec … registered at runtime by `registerInternalOpenApiRoutes`; handlers live in `src/service/routes-openapi/handlers/` and are bound by `operationId`".

Run artifact `kb/route-census.json`: 455 entries. The finding's entrypoint, `POST /v1/vulnerability-sources`, is **not among them**. Of 32 entries matching `vulnerability-source`, the ones sampled are all from `*.test.ts`. The census's first entry is `{"method": "POST", "path": "HeapProfiler.takeHeapSnapshot", "framework": "express"}` and another is `{"method": "GET", "path": "SELECT COUNT(*) AS n FROM Items"}` — the express regex `\.(get|post|…)\(\s*["'`]([^"'`]+)["'`]` matches any method call whose first argument is a string.

The downstream effect is visible in `report.md`: the coverage table's route rows are `GET /hit (…request-id-http-integration.test.ts:48)`, `GET 1 (…get-cve-investigation-details.test.ts:53)`, and similar — 20+ rows of test-fixture noise carrying `needs_follow_up`. Real route gaps are indistinguishable from junk in that table.

**Root cause.** Route discovery is a single-strategy regex with no framework-specific validation and no test-file exclusion. The module's own docstring states its purpose is that "an omission [becomes] visible" — for this target it inverted, hiding omissions inside noise.

**Required behavior.** (1) An OpenAPI strategy: parse `openapi*.yaml` path items plus the `operationId` → handler binding, so spec-declared routes enter the census with their handler file. (2) Exclude test paths from the census by default, or tag them `origin: test` and keep them out of the ledger's follow-up rows. (3) Validate an extracted path shape (leading `/`, no SQL, no dotted identifier) and count rejects as an extraction-quality metric that the run reports. (4) Where a target declares routes in a way no strategy models, that must be an explicit coverage gap, not silence.

**Acceptance test.** Census over comply must contain `POST /v1/vulnerability-sources` bound to its OpenAPI handler, must contain zero entries whose file matches `*test*`, and must contain zero paths failing shape validation.

---

### D-7 — Correlation is a string-join over findings, not a cross-repo dataflow analysis, so a DB-column taint channel is unrepresentable

**Evidence.** `correlate/ingest.py:45-66` — `ingest()` reads each member's `findings.json` and nothing else; no source, no graph, no taint. Two edge derivations exist:
- `control_enforces_edges` (`correlate/edges.py:146-172`) — intersects **quoted substrings** of finding messages (`_privilege_tokens`, `edges.py:126-144`) between an `rbac-source` member and a `service-enforcer` member.
- `same_class_recurrence` (`edges.py:~100-112`) — groups by fingerprint across members.

Roles are limited to `rbac-source`, `service-enforcer`, `infra` (`correlate/manifest.py`, `ROLES`). There is no data-channel edge kind — no DB column, queue, file artifact, or shared schema.

Run output confirms the consequence: `{"edges": 0, "members": 4, "verdicts": 15, "artifacts": 4}`. All 15 verdicts are `direction: "coverage-gap"`, `edge: null`, `evidence_chain: []`, `confidence: "low"` (`verdicts.json`). `artifacts/REDTEAM.md` — cross-repo directives: `_none_`.

This finding's taint crosses `parser.go:112` → `sources.feed_template` → `normal.ts:69`. Even with both members audited in the same run and both files read, the correlation layer has no vocabulary for that edge. A privilege-token string intersection cannot express it, and the two members' findings share no fingerprint.

**Root cause.** The correlation layer models *organizational* relationships between repos (who enforces whose permissions) and not *data* relationships. For a producer/consumer pair joined by storage — which is the normal shape of a build-pipeline-plus-service product — it has nothing to say.

**Required behavior.** A `data-channel` edge kind: a declared or discovered shared channel (DB table.column, queue topic, file artifact, shared schema) with a producing member and a consuming member, and taint semantics — attacker-controlled bytes written by member A into channel C, read by member B into a sink, is one cross-member finding, not two coverage gaps. The manifest must be able to declare channels explicitly (cheap, deterministic, reviewable) even before any discovery heuristic exists. `evidence_chain` must be populated with the producer and consumer `file:line` pair; a verdict with `evidence_chain: []` and `confidence: "low"` on every row is a null result presented as a result.

**Acceptance test.** Given a manifest declaring channel `sources.feed_template` with producer `enrichmentlibrarybuilder` (`vulndb.go:1073`) and consumer `comply` (`normal.ts:69`), correlation must emit a `data-channel` edge and a cross-member verdict whose `evidence_chain` names both sites.

---

### D-8 — Member scoping turned "the caller is out of scope" into a rejection reason instead of a coverage gap

**Evidence.** The `enrichmentlibrarybuilder` investigate agent filed two path-traversal findings and stated the boundary explicitly in its return: `ParseOVAL` has "zero non-test call sites in this repo … reachability is unconfirmed here, not ruled out (real caller is an out-of-scope CLI per arc42)"; `EncryptFile` has "zero callers anywhere in this repo … real consumers live in sibling repos". Both were filed `runtime_dependent`.

Both were then **rejected** at validate. Final state, `findings.json` for that member: `PATH-TRAVERSAL-0001` and `PATH-TRAVERSAL-0002` are `rejected`; only `C-RESOURCE-0001` (confirmed), `C-CRYPTO-0001`, `CRYPTO-0001`, `RESOURCE-0001` survive.

The identical logic applied to the reference finding kills it from the Go side: `parser.go:112` captures raw bytes with no in-repo consumer that treats them as program text, so from inside `enrichmentlibrarybuilder` the capture looks harmless, and the consumer is out of scope. From inside `comply`, the producer is out of scope. Each member's audit is individually defensible and the product-level bug survives both.

**Root cause.** "Unconfirmable within this member" collapses to "not a finding". There is no terminal state for "real defect whose reachability lives in a sibling member", and no mechanism to hand such a finding to the correlation layer as an open obligation.

**Required behavior.** A cross-member obligation state. A finding whose blocker is `caller-out-of-scope` must not be rejectable by a member-scoped validator; it must persist as an open obligation carrying the out-of-scope symbol, and correlation must attempt to discharge it against sibling members' findings and channels. An obligation that no member discharges is a reported coverage gap with the symbol named — not a rejection. `reachability` blocker taxonomy (`sec_overlay.reachability`) needs `caller-out-of-scope` as a first-class, non-fatal blocker distinct from a proven control.

**Acceptance test.** Fixture: member A writes attacker bytes to a channel, member B reads them into a sink; audit each member separately. Neither member may reject its half; correlation must join them into one finding.

---

### D-9 — The proof lane is off by default and cannot oracle this class even when on

**Evidence.** `prove.prove_enabled` (`prove.py:73-88`) — "the lane is off unless `scan_options.prove_findings` is exactly `true`". The run's profile has `scan_options: null`, so the lane never ran. Additionally `prove.py:30-35`:

```python
AUTO_CONFIRMABLE = frozenset({"ssrf", "cmdi", "path-traversal", "deserialization", "expr-eval-rce"})
HARNESS_ONLY     = frozenset({"sqli", "authz"})
```

`ssti` and `injection` are in neither set, so even with the lane enabled a template-injection finding is rejected with `prove: class-not-oracle-able` (`prove._reject_reason`). Meanwhile the competing audit's confirmation came *precisely* from execution — build the Go binary, run the real import, recover the bytes from the DB, compile them through the installed `dot@1.1.3`, execute OS commands, capture the PID and OS user. Two independent refuters reproduced it.

**Root cause.** The one lane that could substitute for the missing static receipt (D-4) is default-off and class-blind to the family in question. `PROVE_TOOLCHAINS` already includes `node`.

**Required behavior.** Add `ssti` and `injection` to `AUTO_CONFIRMABLE` with a wrapper-decidable oracle (compile attacker text through the real engine in a sandboxed child; oracle = observable side effect such as a file write or a process spawn — exactly what the reference reproduction did). Separately, define when the lane should default on: a finding whose only missing receipt is a dependency-internal sink is the strongest possible candidate for proof-by-execution, and leaving it off guarantees a `needs-deployment-testing` ceiling.

**Acceptance test.** With `prove_findings: true` and a fixture `ssti` finding on `dot.template`, the lane must drive a real entrypoint, observe the oracle, and promote the finding — or reject with a reason that is not `class-not-oracle-able`.

---

## 3. Cross-cutting: provenance loss makes these defects hard to see

Three separate places where the run discards the information needed to notice a coverage failure:

1. **Prefilter receipts record nothing.** `run.receipt` (`run.py:102-136`) writes `{phase, stdout, artifacts, counts}` and `drive`'s `on_complete` passes `counts=finding_counts(ws)` only (`run.py:223-225`). The run's `kb/receipts/prefilter.json` is `{"phase": "prefilter", "stdout": "", "artifacts": [], "counts": {"findings": 0}}`. `run_prefilter` returns `{candidates, backends_run, skipped, failed, excluded, dropped_nonsecurity, skipped_reasons}` — **none of it is persisted**. Grepping the entire comply workspace for `backends_run` returns nothing. The run cannot answer "did CodeQL JavaScript actually run, and how many findings did `security_only` delete", which are the two questions this report needed most.
2. **`dropped_nonsecurity` is a bare integer** (D-2) — no ids, no rules, no files.
3. **The self-score measures throughput, not coverage.** `state.json` `budget.self_score` = `{reported: 9, confirmed: 9, needs_runtime: 9, rejected: 246, clusters: 0, external_boundary: 6, shipping: 18, critic_viable: 11, critic_rejected: 0, critic_reject_rate: 0.0}`. Nothing in it would move if an entire attack class were absent. `critic_reject_rate: 0.0` across 11 viable findings is itself an unexamined signal that a gate is not discriminating.

**Required behavior.** Persist each phase's own return value in its receipt verbatim, including `backends_run`, `skipped_reasons`, `failed`, and a per-finding drop ledger. Add coverage-shaped metrics to the self-score: floor classes investigated vs. excluded, catalog entries matched per ecosystem, route-extraction reject rate, obligations opened vs. discharged.

---

## 4. Why the gates all reported green

Worth stating for the spec, because the run's own quality machinery signed off on an audit missing an authenticated RCE:

- `kb/gates/recall-gate.json` — `{"passed": true, "errors": [], "warnings": []}`. It checks route census and catalog classes; both were blind here (D-3, D-6).
- `kb/gates/artifact-gate.json`, `kb/gates/artifact-consistency.json` — `{"passed": true, "errors": []}`. Deterministic self-checks on artifact presence and internal consistency; neither models coverage.
- `kb/gates/artifact-review.json` — the opus adversary returned `verdict: "re-render"` and did real work: it caught that the "8 critical" headline rested on 8 osv lockfile findings with `reachability.reachable=false`, empty impact, no CVSS vector, 7 of 8 flagged `"dev": true` in their own lockfiles. It is a claim↔evidence auditor over what the report *says*. It has no view of what the report *omits*.
- `coverage-ledger` — correctly `partial`, with 11 rows. Every row is a class recon named. The one thing wrong with the audit is not expressible in its vocabulary (D-5).

The pattern: every gate validates the pipeline against its own inputs. No gate validates the inputs against the target. That is the single structural theme behind D-1, D-3, D-5, D-6, and D-7.

---

## 5. Priority for the spec

| # | Defect | Cost to fix | Would it alone have surfaced the finding? |
|---|---|---|---|
| D-3 | No npm entries in dependency-sink catalog | Low — data | Yes — routes `ssti` into `agents_to_spawn` deterministically |
| D-1 | CWE-94/95 unmapped; `injection` class unroutable | Low — data | Partially — needs D-2 to survive prefilter |
| D-2 | `security_only` silently deletes `unknown` semgrep hits | Low — logic | Partially — needs D-1 to have a class |
| D-4 | No `dependency-catalog` receipt kind; prompt contradicts gate | Medium | Yes — lets a correct agent finding reach `confirmed` |
| D-5 | No mandatory class floor; ledger is a closed loop | Medium | Yes — forces the class to be investigated or excluded |
| D-6 | Route census blind to OpenAPI; test noise | Medium | Partially — surfaces the entrypoint for hunting |
| D-9 | Proof lane off by default, class-blind | Medium | Yes — reproduces it, as the competing audit did |
| D-7 | No cross-repo data-channel edge | High | Yes — the finding's true shape |
| D-8 | Out-of-scope caller ⇒ rejection | Medium | Yes — stops both halves being discarded |

Cheapest credible combination that surfaces this exact finding: **D-3 + D-1 + D-2 + D-4**. Cheapest combination that surfaces the *class* of finding (cross-member taint through storage): **D-7 + D-8**.

---

## 6. Evidence index

Plugin (1.122.0 paths; 1.107.3 equivalence noted inline where the audited run differs):
```
helpers/sec_overlay/clsmap.py:17-30, 38-68, 131-163      CWE map, rule-id fallback, class resolution
helpers/sec_overlay/prefilter.py:180-220, 289-296        codeql unit, security_only drop
helpers/sec_overlay/partition.py                          demote_noise, reconcile_plan
helpers/sec_overlay/dependency_sinks.py:139-215           manifest/indicator matching
helpers/sec_overlay/sast.py:16, 37-39                     semgrep severity map, cls assignment
helpers/sec_overlay/route_census.py:20, 72-86             skip globs, regex extraction
helpers/sec_overlay/findings_gate.py:50-58                tool-receipt gate
helpers/sec_overlay/evidence.py  (_MECHANICAL)            receipt whitelist
helpers/sec_overlay/prove.py:30-35, 73-88                 oracle classes, opt-in gate
helpers/sec_overlay/correlate/ingest.py:45-66             findings-only ingest
helpers/sec_overlay/correlate/edges.py:126-172            privilege-token join
helpers/sec_overlay/correlate/manifest.py  (ROLES)        3 roles, no channels
helpers/rules/semgrep/javascript/lang/security/detect-eval-with-expression.yaml
helpers/rules/semgrep/javascript/lang/security/audit/code-string-concat.yaml
references/dependency-sinks.json                          6 entries: 5 go, 1 python
references/route-frameworks.json                          7 frameworks, no OpenAPI
agents/classes/ssti.md:28-30, 38-41                       injection routing; dependency-catalog receipt
```

Run artifacts (`comply/.sec-overlay/comply-3c82b976/`):
```
kb/scan-profile.json          attack_surface (12), agents_to_spawn (11), sast_plan, scan_options: null
kb/route-census.json          455 entries; entrypoint absent; test + junk paths present
kb/coverage-ledger.json       completeness: partial; 11 class rows, all needs_follow_up
kb/receipts/prefilter.json    counts.findings=0; no backends_run / skipped_reasons / dropped ids
kb/gates/*.json               recall, artifact, artifact-consistency all passed
runs/investigate.txt          "14 investigate class agents completed (…)"
state.json                    budget.self_score — throughput only
report.md:213+                coverage table, route noise rows
```

Correlation output (`comply/`): `edges.json` (empty), `verdicts.json` (15 × coverage-gap, `evidence_chain: []`), `artifacts/REDTEAM.md` (`_none_`).

Audited target (comply @ `a398fceee3da`): `normal.ts:69-70`, `util/templates.ts:93-95`, `src/service/package.json:127`, `node_modules/` absent.
