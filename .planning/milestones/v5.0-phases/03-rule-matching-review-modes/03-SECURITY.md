---
phase: 03
slug: rule-matching-review-modes
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-19
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

The register below is the union of the `<threat_model>` blocks in `03-01-PLAN.md` through
`03-07-PLAN.md`. Both SUMMARY threat-flag sections (03-05, 03-06) report no threat outside
this register. Each closed row cites the mechanical evidence that the L1 check found.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| repo file tree → `rule_glob` | Rule-doc paths and diff file paths cross into filesystem reads | file paths, rule-doc text |
| `--rule` CLI argument / `rule.json` layers → filesystem | Operator- and repo-controlled paths are opened for reading | arbitrary file paths |
| rule-doc / rule-file text → reviewing agent prompt | Repo-controlled markdown becomes the agent's instruction block | untrusted prompt text |
| diff text → rendered review prompt | Attacker-influenced source text enters a model prompt | untrusted diff text |
| review-file subagent return → `parse_review_response` | An untrusted model response asks for findings to be created | model output |
| review-filter subagent return → `reflection.validate_verdict` | An untrusted model response asks for findings to be removed | model output |
| recorded agent return on disk → `run_review` | A file written between two CLI invocations is read back as run input | recorded model output |
| parsed findings → position, profile, reflection, receipt gates | Model-authored findings cross into the shipping pipeline | findings |
| harness → published ledger | `review_ledger.json` and `report.md` are what a human acts on | report artifacts |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering | `rule_glob.builtin_rule_docs_dir` | medium | mitigate | Docs directory resolved from `Path(__file__)`, never cwd or env (`rule_glob.py`; same discipline mirrored in `review_agent.py:53`) | closed |
| T-03-01 | Tampering | `read_rule_file_safe` | high | mitigate | Symlink resolve → `is_relative_to` repo-root check → suffix allowlist (`rule_glob.py`, 3 resolve/containment refs) | closed |
| T-03-02 | Denial of Service | `read_rule_file_safe` | high | mitigate | `MAX_RULE_FILE_BYTES = 524288` enforced on the read itself, reads at most cap+1 bytes and rejects on overflow (`rule_glob.py:48,305,322`) | closed |
| T-03-03 | Tampering | rule text injected as agent rule block | high | mitigate | Rule text enters inside the data envelope; receipt gate in `findings_gate.py` reads no rule text; doc-content prohibition enforced by `test_rule_docs.py` conformance checks | closed |
| T-03-04 | Elevation of Privilege | `reflection.apply_verdict` | high | mitigate | Retract-only by parsing; ids outside submitted set raise; `PROTECTED_SUBJECT_CLASSES` code veto (4 refs in `reflection.py`, D-16) | closed |
| T-03-05 | Repudiation | `report.write_review_ledger` | medium | mitigate | Retraction/refusal/fail-open each get a ledger entry; zero case renders an explicit sentence (16 ledger refs in `report.py`, D-14/D-15) | closed |
| T-03-06 | Elevation of Privilege | `apply_profile` | medium | mitigate | Bypass restricted to frozenset of five classes; gates C/D/E unconditional; unknown profile raises (`review_findings.py`, 9 allowlist refs) | closed |
| T-03-08 | Denial of Service | `reflection` per-file loop | medium | mitigate | Per-file `try`/`except` records a skip and continues (`cli.py`, 7 handlers); one bad file cannot abort the run | closed |
| T-03-09 | Elevation of Privilege | global `~/.sec-overlay/rule.json` layer | medium | mitigate | Global layer's rule files pass the same `read_rule_file_safe` gate incl. repo-root containment | closed |
| T-03-10 | Denial of Service | `resolve_rule_doc` map-referenced read | low | mitigate | Conformance test proves every map value resolves to an existing non-empty file (`test_rule_docs.py`, 8 map refs) | closed |
| T-03-11 | Repudiation | orphan doc or orphan map entry | low | mitigate | Test asserts both directions of map↔file relationship (`test_rule_docs.py`) | closed |
| T-03-12 | Spoofing | model-supplied `defect_class` | medium | mitigate | `classify` returns `str | None`, accepts only `GENERAL_DEFECT_CLASSES` values; class can never reach `confirmed` (`review_findings.py:92`) | closed |
| T-03-13 | Repudiation | profile provenance in output | low | mitigate | Ledger records profile and defect class per record (`report.py`) | closed |
| T-03-14 | Tampering | `references/prompt-constants.md` | high | mitigate | `EXCLUSION_RULES` block present and append-only per plan acceptance criterion (2 refs in `prompt-constants.md`) | closed |
| T-03-15 | Elevation of Privilege | `findings_gate` disposition ladder | high | mitigate | Ladder assigns only non-shipping dispositions; `confirms_alone` remains the sole path to `confirmed`; unknown class raises (`disposition_without_receipt` in both modules, REV-03) | closed |
| T-03-16 | Tampering | prompt injection via diff or finding text | high | mitigate | Protected-subject veto at prompt step 1 plus code veto backstop; only `code_comment`/`task_done` shapes accepted, anything else raises (`review_agent.py:33-34,121`) | closed |
| T-03-17 | Tampering | rendered review prompt | high | mitigate | `review-file.md` imports `ANTI_MANIPULATION` and `TOOL_TRUST` and wraps repo text in the `<untrusted nonce>` envelope (`agents/review-file.md:36`) | closed |
| T-03-18 | Elevation of Privilege | `parse_review_response` | critical | mitigate | Evidence stamped `llm-claimed:review-agent` in code (3 refs), model-supplied sources dropped; `confirms_alone` fails for every agent-authored finding; status assigned by module (REV-03) | closed |
| T-03-19 | Spoofing | `recorded_return_source` | high | mitigate | Returns keyed by path-derived label and checked against run base/head refs; mismatch refused and ledgered as skip (`review_agent.py` ref checks, `report.py:869`) | closed |
| T-03-20 | Information Disclosure | `runs/review_prompts/` | medium | mitigate | Rendered prompts written only inside the self-ignoring in-repo workspace sidecar (`cli.py` review_prompts refs); no path outside plugin/workspace | closed |
| T-03-21 | Repudiation | review source ledger | medium | mitigate | Missing return, ref mismatch, unparseable return each produce `review_source_skipped` naming path and cause; zero case explicit (`report.py:391,786,869`, D-15) | closed |
| T-03-22 | Denial of Service | per-file source loop | medium | mitigate | Same fail-open handler pattern as reflection; one file's failure records a skip and continues | closed |
| T-03-07-01 | Tampering | `cli.run_review` reflection loop | high | mitigate | Every removal routes through `apply_verdict`; rebind filters strictly on ids `apply_verdict` declined to keep; verified end-to-end by `test_review_live.py` retraction tests (03-07, commit `fb5aca7`) | closed |
| T-03-07-02 | Repudiation | ledger `review_findings` vs `reflection_retractions` | medium | mitigate | Every removal pairs with a `reflection_retractions` entry; per-file failure produces `reflection_skipped` and zero removals (D-14) | closed |
| T-03-07-03 | Elevation of Privilege | `review_findings.apply_profile` disposition | high | mitigate | `disposition_without_receipt` raises on unknown class; test asserts kept set never contains `confirmed` (03-07, commit `45dafc1`) | closed |
| T-03-07 | Information Disclosure | `RuleSafetyError` message | low | accept | See Accepted Risks Log R-03-01 | closed |
| T-03-07-04 | Information Disclosure | rewritten test fixtures | low | accept | See Accepted Risks Log R-03-02 | closed |
| T-03-SC | Tampering | npm/pip/cargo installs | high | accept | See Accepted Risks Log R-03-03 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-03-01 | T-03-07 | `RuleSafetyError` names the rejected path on a local CLI writing to stderr; the operator supplied the path or their repo contains it, and naming it is what makes the error actionable (D-08) | plan 03-02 threat model (plan-time disposition) | 2026-08-19 |
| R-03-02 | T-03-07-04 | Test fixtures are synthetic paths and synthetic findings under `tmp_path`; no real repository content is embedded | plan 03-07 threat model (plan-time disposition) | 2026-08-19 |
| R-03-03 | T-03-SC | No package is installed by this phase; `helpers/pyproject.toml` keeps `dependencies = []` (confirmed on disk) under REL-03; RESEARCH.md Package Legitimacy Audit records zero proposed packages | plan 03-01..03-07 threat models (plan-time disposition) | 2026-08-19 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-19 | 27 | 27 | 0 | secure-phase orchestrator (L1 grep verification; short-circuit — register authored at plan time, ASVS 1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-19
