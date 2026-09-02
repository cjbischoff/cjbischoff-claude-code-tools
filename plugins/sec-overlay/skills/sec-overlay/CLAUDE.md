# CLAUDE.md — sec-overlay skill operating manual

This file is the operational companion `SKILL.md` points to for running this security-audit skill
against real codebases. Maintainer content lives in `plugins/sec-overlay/CLAUDE.md`.

---
## 0. Mission — what a good run produces

Run this harness on a target codebase to find **actually-exploitable** vulnerabilities and hand a
security engineer artifacts they can act on, in priority order:

1. **Signal over noise.** A finding a human acts on must be real. Confirmation requires a
   **mechanical tool receipt** — LLM reasoning alone never confirms. False positives are a defect.
2. **Exploitability, not pattern-matching.** A syntactic match is a *candidate*, not a finding. The
   bar is a traced source→sink with attacker control and reachability, or an explicit
   `needs-runtime` disposition telling a human exactly what to test on a live system.
3. **Artifacts an engineer can use.** Every run leaves a threat model, per-finding JSON with
   evidence + reachability, a SARIF file, a Markdown report, and a `redteam-plan.md` test plan.

Recall matters too: coverage is pursued until a phase can defend it to its adversary; gaps are
**logged, never dropped**. Uncertain findings stay `raw`/`candidate`, never deleted on a hunch.

---
## 1. Environment prerequisites for a full run

Before a *full* audit, satisfy these environment prerequisites (a clean checkout lacks them):

- **Vendored semgrep ruleset** — `rules/semgrep/` is a gitignored, shallow-cloned directory
  (`git clone --depth 1 https://github.com/semgrep/semgrep-rules rules/semgrep`, per
  `preflight.py`'s remediation), not a tracked sub-repository. It must be present or
  `test_preflight.py::...vendored_rules` fails for lack of rules.
- **External tool binaries** — `uv run python -m sec_overlay.preflight` must show `semgrep`,
  `codeql` (+ query packs), `ast-grep`, `osv-scanner`; a missing pack drops that dataflow (§2).
- **Bench corpus ships committed** — `bench/corpus_seed/*.json` holds only public entries (public-app
  advisories pinned to a commit, dep-CVE lockfiles, and synthetic fixtures under `helpers/fixtures/`),
  so `test_bench.py::test_seed_corpus_is_valid`, `test_seed_corpus_has_min_entries`, and
  `test_citations.py::test_all_mapped_ids_exist_in_seed` run in CI, not just locally. The corpus is
  still **dev/bench** — a grading oracle, not part of an audit run. Never add a confirmed vuln from
  private code to the seed.

---
## 2. How to run an audit

The **main agent orchestrates**; deterministic steps run via `uv run` from
`skills/sec-overlay/helpers/`; agent steps spawn a subagent with the named `agents/*.md` prompt
(tokens like `{{TARGET}}`/`{{WORKSPACE}}`/`{{ATTACK_CLASS}}` substituted through
`sec_overlay.prompts.render_prompt`, which fails loudly on any unfilled `{{token}}`). Record each
phase with `record_stage(<WS>, "<phase>")` so passes advance. `SKILL.md` is the full operational
playbook — read it before driving a run; this section is the map.

Legend: `<T>` target repo, `<WS>` workspace, `<sha>` = `git -C <T> rev-parse HEAD`, `<rules>` a
local semgrep ruleset.

### Phase order (one pass)

The generated table and the per-phase operator notes both live in [`SKILL.md`](SKILL.md) — read
its "Running a full audit" section for the full phase order, one row per `PHASE_TABLE` entry, and
the command or prompt each phase runs. This file stays a maintainer quick-map and does not
duplicate either.

### Quick deterministic scan (no agents)

```bash
cd skills/sec-overlay/helpers
uv run python -m sec_overlay.cli scan \
  --target <T> --workspace <WS> --config rules/smoke.yaml \
  --sha "$(git -C <T> rev-parse HEAD)"
```
Emits `findings/F-*.json`, `report.sarif`, `report.md` — a fast smoke path, not a real audit.

### Hard operating rules during a run

- **A scan is clean only if every PLANNED backend ran.** STOP on a setup error if `run_prefilter`
  returns empty `backends_run`, or a planned backend appears in `failed`/`skipped_reasons` (e.g.
  `codeql: pack-missing` = zero dataflow) — a partial scan is a **coverage hole**, not "no findings".
  Run `codeql pack download codeql/<lang>-queries` if a pack is missing.
- **Do not orphan candidates.** Classes beyond `agents_to_spawn` (e.g. `security-other`, `unknown`)
  need `unrouted_candidate_classes(ws, agents_to_spawn)` checked — spawn a general-triage agent if non-empty.
- **Fan-out under provider load:** dispatch parallel agents in waves of ~3–4 — a transient 429/529
  can wipe a one-message batch. Re-dispatch is safe: skip classes whose candidates are all non-`candidate`.
- **Phase completion:** a phase is done only when ALL its outputs exist AND `record_stage` ran —
  never infer completion from one file's presence.
- **Multi-pass (pass N>1):** scope to changed code with `diffscope.changed_files(<prior_sha>, "HEAD")`;
  `carry_forward(...)` re-checks settled findings on changed files (→ `stale`), keeps unchanged ones — full re-scan is the safe default, incremental is the token optimization.
- **The Tier-1 substrate is always built**, never behind a flag; `no_path` receipts are only valid
  after Tier-2 taint merge at prefilter.

---
## 3. Signal-over-noise architecture (why findings are trustworthy)

This is the core value of the harness. Four layered mechanisms — do not weaken any of them:

**a) Tool-receipt confirmation gate.** A finding reaches `confirmed`/`fixed` only with ≥1
`evidence_sources` entry `evidence.is_tool_receipt()` accepts (`findings_gate.py:50-58`). The
whitelist (`evidence.py` `_MECHANICAL`): `semgrep`, `codeql`, `ast-grep`, `tree-sitter`, `ripgrep`,
`structural-index`, `secrets`, `sca` — colon form `semgrep:<rule>`, `codeql:dataflow`, etc. LLM
assertions are `llm-claimed:*` and **corroborate but never confirm**.

**b) Gate ladder in `investigate.md`** (each rung needs a recorded receipt): Gate −1
sanity/hallucination (cited code absent/different → DISCARD), Gate 0 design intent, Gate 1
reachability, Gate 2a attacker control, Gate 2b sanitizer scope (never trust a function *named*
`sanitize`/`validate`), Gate 3 new capability. Investigate is **recall-biased** (keep unsure as
`raw`); later stages are precision-biased.

**c) Adversarial validation with model-family diversity.** Every load-bearing artifact is
pressure-checked by an adversary on a **different, stronger model family** than the producer (opus
vs the sonnet producer) — mandatory; with only one family available, degrade to a fresh-context
validator and **log it**. Findings: `critic` → `judge` → `validate` (tries to *refute*; survival
= confirmation). Context/analysis phases use `phase-adversary.md`, `context-adversary.md`, or
`redteam-adversary.md`, plus a deterministic `phase_gate.run_phase_checks` rejecting claims whose
cited `file:line` doesn't resolve. **Safety contract:** adversarial *reasoning* alone
demotes/downgrades but never deletes a tool-receipt-backed finding — only a competing receipt can.

**d) Derived severity + FP discipline.** `SEVERITY_PRECONDITION` forces preconditions enumerated
*before* a severity band; the harness computes CVSS, not the LLM. `validate.md` requires a
`file:line` citation to reject as false-positive and never launders a `verify-error` into a clean
verdict. `needs-deployment-testing` is a real terminal state for real-but-unprovable findings —
never folded into `confirmed` or `rejected`.

**The static→runtime bridge (`redteam-plan.md`)** is where exploitability judgment reaches the
human: `runtime_disposition` splits `static-settled` from `needs-runtime`; only findings at/above
the confidence bar (`risk_score >= min-risk`, default 7) become manual test directives. The harness
**never executes the target** — it emits a plan a human runs.

---
## 4. Workspace artifacts (what a security engineer gets)

Default workspace: `<target>/.sec-overlay/<repo-slug>/` — an in-repo, self-ignoring sidecar next
to the reviewed code (override base `$SEC_OVERLAY_HOME`; override entirely with `--workspace`).
The read-only invariant is about the reviewed **source**, not this folder.

```
kb/scan-profile.json     recon output: languages, frameworks, attack_surface, sast_plan, subsystems
architecture/            C4 diagrams + runtime views + arc42.md (building blocks in §5)
threat-model/            dfd.mmd (derived) + attack-sequences/ + threat-model.md (findings, hunt list)
kb/context.json          repo's own docs distilled (trust-tagged untrusted-doc / prior-scan)
kb/gates/<phase>.json    adversary verdict audit trail per gated phase
kb/gates/arch-gate.json, tm-gate.json    deterministic arch/tm gates (diagram caps, STE prose, dup)
kb/discovery-ledger.json investigate saturation state (waves, consecutive_no_new, terminal_reason)
kb/coverage-ledger.json  surface-completeness ledger; `complete` machine-rejected while gaps remain
findings/<ID>.json       every finding, all statuses — evidence_sources, reachability, cvss, patch_diff
report.sarif             SARIF 2.1.0 (confirmed/fixed)
report.md                human report (finding-template.md structure; links redteam-plan.md)
kb/gates/artifact-gate.json, artifact-review.json   self-check + opus adversary verdict on report
redteam-plan.md          manual runtime test plan — the engineer's follow-up
state.json               campaign state (pass number, pinned SHA, stages)
MEMORY.md, learnings/     durable per-repo memory across runs
```

Resume an interrupted campaign: `python -m sec_overlay.cli memory --target <T>`.

---
## 5. Reference knowledge — consult, don't guess

Under `references/`. Agents load these by target type; know when each applies:

- **`prompt-constants.md`** — sixteen verbatim blocks (`ANTI_MANIPULATION`, `EXCLUSION_RULES`,
  `GENERAL_PROFILE_EXCLUSION_RULES`, `SEVERITY_GUIDANCE`, `SEVERITY_PRECONDITION`, `SHAPE_HUNTING`,
  `EXHAUSTIVENESS`, `TOOL_TRUST`, `PATH_BASE`, `OUTPUT_WRITE_FALLBACK`, `DIAGRAM_STYLE`,
  `FIELD_OWNERSHIP`, `FINDING_SHAPES`, `QUALIFIER_PROOF`, `EVIDENCE_VOCABULARY`, `STE_PROSE`)
  injected into **every** agent so these rules never drift; all agents wrap untrusted repo text in
  the trust envelope and import these.
- **`attack-classes.md`** — attack-class keys + ripgrep indicators; recon fills `agents_to_spawn`.
- **`hunting/`** — exploit-reasoning companions, loaded conditionally: `methodology.md` +
  `anti-patterns.md` (always, the operational core), `business-logic.md`, `web-protocol-auth.md`
  (proxies/JWT/OAuth/SAML), `ai-agent.md` (LangChain/MCP/RAG), `memory-native.md` (C/C++/Rust-unsafe/
  cgo only), `client-side.md` (SPA/browser).
- **`codeguard/`** — 7 secure-coding checklists per domain, guiding patch/triage remediation shape.
- **`approved-crypto-algorithms.yaml` / `approved-key-sources.yaml`** — machine-checked by
  `crypto_policy.check` (denies md5/sha1/des/ecb, floors rsa≥3072/pbkdf2≥100000/ecc≥256, denies
  literal key sources): "weak crypto" becomes a deterministic lookup.
- **`asvs/asvs_5.0.0.json`** (12-item seed), **schemas** (`scan-profile`, `fix-disposition`),
  **`finding-template.md`** (9-section report bound to `Finding`), and **`DETECTION_COVERAGE.md`**
  (tool-coverage gaps: Liquid/Handlebars templates, single-function OSS-semgrep taint, no CodeQL for PHP).
