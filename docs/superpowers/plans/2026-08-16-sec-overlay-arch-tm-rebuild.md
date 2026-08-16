# sec-overlay Architecture/Threat-Model Phase Rebuild Implementation Plan (Plan 3 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the `architecture` and `threat_model` phases around the C4/arc42 and DFD/STRIDE standards, wire the Plan-2 gates in as phases, and re-point every consumer of the old artifacts.

**Architecture:** The two agent prompts are rewritten to emit the `<workspace>/architecture/` and `<workspace>/threat-model/` trees. Path helpers centralize in `kb.py`. Two new deterministic phase rows run the Plan-2 diagram gate and STE linter after each producer. Old artifacts (`kb/architecture.md`, `kb/entities/`, `kb/THREAT_MODEL.md`) are removed outright; sixteen consumer files re-point.

**Tech Stack:** Python 3.13 stdlib; markdown prompts; pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-08-16-architecture-threat-model-standards-design.md` (§3, §4, §7). Requires Plans 1 and 2 merged (`cvss40_base`, `run_diagram_gate`, `lint_prose`, `check_duplication` all exist).

## Global Constraints

- Branch `feat/architecture-threat-model-standards`; Conventional Commits `<type>(sec-overlay): <summary under 50 chars>`; run from `plugins/sec-overlay/skills/sec-overlay/helpers/` with `uv run`; stdlib-only; TDD for code tasks.
- Doc-guard: `sec_overlay/*.py` → stage `sec_overlay/README.md`; `tests/*.py` → `tests/README.md`; `agents/*.md` → `agents/README.md`; `references/*` → `references/README.md`; `skills/sec-overlay/CLAUDE.md` → `skills/sec-overlay/README.md`. Every commit stages `plugins/sec-overlay/CHANGELOG.md` and bumps `plugins/sec-overlay/.claude-plugin/plugin.json` (feat → minor, docs/test → patch). Explicit paths only; never `--no-verify`; no `Co-Authored-By`.
- **Preserve prompt hard rules verbatim** when rewriting `agents/*.md`: the trust envelope, imported constant names, the "writing files IS your task" + OUTPUT_WRITE_FALLBACK contract, the enumerate-all-controls rule, and the keep-every-entrypoint rule. These blocks move, they do not soften.
- `skills/sec-overlay/CLAUDE.md` must stay under 200 lines (currently 199) — compress existing wording to fit any addition.
- Prompt render contract: only `{{TARGET}}`, `{{WORKSPACE}}`, `{{OVERLAY_ROOT}}` tokens; `render_prompt` fails on anything else. `tests/test_contracts.py` + `tests/test_wiring.py` must stay green.
- Environmental test failures to ignore: `test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`, `test_citations.py::test_all_mapped_ids_exist_in_seed` (may pass).
- Caps and derivation header format are Plan 2's: `%% derived-from: <source-filename> sha256:<64-hex>`.

---

### Task 1: Reference files + STE_PROSE prompt block

**Files:**
- Create: `references/architecture-standards.md`
- Create: `references/threat-model-standards.md`
- Create: `references/mermaid-caps.md`
- Modify: `references/prompt-constants.md` (append the `STE_PROSE` block)
- Modify: `references/README.md`
- Test: `tests/test_references_caps.py` (new)

**Interfaces:**
- Consumes: `CAPS`, `SEQ_CAPS` from `sec_overlay.diagram_gate` (Plan 2).
- Produces: three reference files Tasks 3–4 import by name; a `STE_PROSE` block named exactly like the other prompt-constants blocks; a test binding the md caps table to the gate constants.

- [ ] **Step 1: Write the failing caps-consistency test**

```python
# tests/test_references_caps.py — new
import re
from pathlib import Path

from sec_overlay.diagram_gate import CAPS, SEQ_CAPS

_CAPS_MD = Path(__file__).resolve().parents[1].parent / "references" / "mermaid-caps.md"


def test_caps_table_matches_gate_constants():
    text = _CAPS_MD.read_text()
    rows = dict(re.findall(r"^\|\s*([a-z-]+)\s*\|\s*(\d+)", text, re.MULTILINE))
    assert int(rows["context"]) == CAPS["context"]
    assert int(rows["container"]) == CAPS["container"]
    assert int(rows["component"]) == CAPS["component"]
    assert int(rows["dfd"]) == CAPS["dfd"]
    assert int(rows["sequence-participants"]) == SEQ_CAPS[0]
    assert int(rows["sequence-messages"]) == SEQ_CAPS[1]
```

- [ ] **Step 2: Run, confirm red** — `uv run pytest tests/test_references_caps.py -v` (file missing).

- [ ] **Step 3: Write `references/mermaid-caps.md`**

```markdown
# Mermaid generation rules (hard constraints)

Exceeding any cap is a generation failure, not a warning. `sec_overlay.diagram_gate`
enforces this table mechanically; `tests/test_references_caps.py` keeps the two in sync.

| kind | cap | counts |
|---|---|---|
| context | 10 | nodes (external systems/actors) |
| container | 15 | nodes per bounded system |
| component | 10 | nodes per container |
| dfd | 12 | processes + data stores + external entities (boundaries excluded) |
| sequence-participants | 6 | participants per sequence diagram |
| sequence-messages | 15 | messages per sequence diagram |

## Generation rules
1. One diagram, one story — structure, behavior, and trust boundaries never share a diagram.
2. Node labels: name only. Edge labels: verb phrase, 4 words or fewer.
3. No orphan detail: a single-edge node that is not an actor or data store folds into prose.
4. Grouping over enumeration: more than 3 similar elements collapse to one counted node
   ("Downstream tools (5)") with the members in a table below the diagram.
5. DFD trust boundaries are `subgraph` blocks — structural, never a decorative label.
6. Re-scoping on cap breach, in order: **group** (rule 4), then **split** (one diagram per
   bounded sub-scope, e.g. "request path" and "async settlement path"), then **promote**
   (remaining excess moves to a summary table in prose). Never emit an over-cap diagram.
7. No decorative styling. Any non-default style requires a legend on or below the diagram.
8. Derived diagrams carry `%% derived-from: <source-filename> sha256:<hex-of-source>` and
   introduce no element or participant absent from their source.
```

- [ ] **Step 4: Write `references/architecture-standards.md`**

```markdown
# Architecture documentation standard (C4 + arc42)

## Diagrams — C4, rendered as Mermaid
- **context-diagram.mmd** — the system plus external actors/systems only.
- **container-diagram.mmd** — deployable units and the protocols between them. This is
  the single source of truth for system structure; the threat model's DFD is derived
  from it, never redrawn.
- **component-diagram-<name>.mmd** — only for containers the scan profile flags
  high-complexity. Most containers get none.
- **runtime-view/sequence-<scenario>.mmd** — normal-path sequence diagrams, only for
  scenarios with branching, retries, async handoffs, or ordering the container diagram's
  arrows do not already imply.
All diagrams obey `mermaid-caps.md`.

## Document — arc42.md
| Section | Content |
|---|---|
| 1. Introduction & Goals | Requirements, stakeholders, top quality goals |
| 2. Constraints | Technical/organizational constraints |
| 3. Context & Scope | embeds/points to context-diagram.mmd |
| 4. Solution Strategy | core design decisions inferred from code, with file:line evidence |
| 5. Building Block View | points to container/component diagrams; one block per
security-relevant component: name, responsibility, key files (path:line), inputs it
trusts/untrusts. This replaces the old kb/entities/ files — later agents read these blocks. |
| 6. Runtime View | points to runtime-view/ sequences, key scenarios only |
| 7. Deployment View | infrastructure/deployment topology |
| 8. Crosscutting Concepts | cross-cutting technical topics |
| 10. Quality Requirements | as evidenced |
| 11. Risks & Technical Debt | non-security technical debt only |
| 12. Glossary | one line per kept domain term |
Section 9 (Architecture Decisions) is omitted: a read-only scanner cannot author ADRs.

## Ownership boundary (hard)
Owns: purpose, tech stack, deployment topology, component structure, rationale, quality
attributes, normal-path runtime behavior.
Never contains: threats, attack surface, mitigations, findings. Trust boundaries appear
ONLY as structure (which zone contains what), never with attacker narrative.
```

- [ ] **Step 5: Write `references/threat-model-standards.md`**

```markdown
# Threat model standard (DFD + STRIDE, signal-augmented)

## Methodology selection (run once, record the outcome)
1. STRIDE always — a full pass over every DFD element at every boundary crossing.
   Unconditional, never part of the augmentation decision.
2. Augment by signal:
   - auth/credential issuance, payment/financial flow, high business-impact path → add PASTA
   - PII fields, consent flows, user data stores, GDPR/CCPA handling → add LINDDUN
   - both signal sets → both; neither → STRIDE alone.
3. Record applied methodologies + the one-line signal justification at the top of
   threat-model.md. Per-system decision; never a hardcoded combination.

## Derived diagrams
- **dfd.mmd** derives from `architecture/container-diagram.mmd`: same element ids,
  implementation detail stripped, `subgraph` per trust boundary (network zone, auth,
  process, third-party), data-classification labels on flows where determinable
  (credentials, PII, tokens). Carries the derived-from SHA header.
- **attack-sequences/sequence-<attack>.mmd** derive from runtime-view sequences: same
  participants, attack steps inserted or timing assumptions violated. For classes STRIDE
  tables under-represent: races, TOCTOU, token replay, multi-boundary chains. Each ties
  to one findings-table row.

## Findings table columns
threat | affected DFD element | STRIDE/LINDDUN category | CVSS v4.0 score + vector |
existing mitigation (if evidenced) | residual risk | recommended mitigation
The agent proposes the vector; the harness computes the score. ATT&CK technique ids are
cited in the finding text for adversary-realistic findings.

## Ownership boundary (hard)
Owns: trust boundaries, per-crossing threats, attack surface, findings, mitigations,
attack sequences, the prioritized hunt list.
Never restates: system purpose/structure narrative, deployment rationale, tech-stack
justification — reference arc42 by section (`see arc42 §4`) instead.
```

- [ ] **Step 6: Append `STE_PROSE` to `references/prompt-constants.md`**

Follow the file's existing block format (heading + fenced block, matching the other twelve). Content:

```markdown
## STE_PROSE

Prose you write for humans (arc42.md, threat-model.md, findings-table free text) follows
ASD-STE100's checkable core. Hard rules: active voice; one instruction or claim per
sentence; sentences ≤25 words; no semicolons; noun clusters ≤3 words; paragraphs ≤6
sentences on one topic; numbered/bulleted list for any 3+ step sequence. Lexical rules
are directional: one word per meaning (pick one verb per action and reuse it), verb over
noun form, define kept domain terms once in the glossary. Preserve every hedge and scope
qualifier — "may have failed" never becomes "failed"; when the tense rule and a hedge
conflict, the hedge wins. Put the one-time statement "Prose follows an ASD-STE100-inspired
clarity standard (structural rules enforced; lexical dictionary not verified)." in the
document front matter. A deterministic linter rejects sentence/semicolon/paragraph
violations, so write compliant the first time. Diagram labels are governed by
mermaid-caps.md, not this block.
```

- [ ] **Step 7: Run, confirm green** — `uv run pytest tests/test_references_caps.py tests/test_contracts.py -q && uv run ruff check tests/`

- [ ] **Step 8: Commit**

```bash
git add references/architecture-standards.md references/threat-model-standards.md \
  references/mermaid-caps.md references/prompt-constants.md references/README.md \
  helpers/tests/test_references_caps.py helpers/tests/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): add C4/arc42, DFD/STRIDE, STE references"
```

---

### Task 2: Path helpers and workspace directories

**Files:**
- Modify: `sec_overlay/kb.py:16-23` (replace the two path helpers, extend `kb_status`)
- Modify: `sec_overlay/workspace.py` (`ensure()` creates the new trees)
- Test: `tests/test_kb.py` (or create if absent), `tests/test_workspace.py` (append)

**Interfaces:**
- Consumes: `Workspace` (`ws.root`, `ws.kb`).
- Produces (all later tasks and prompts use these paths):
  - `arch_dir(ws) -> ws.root / "architecture"`
  - `arc42_path(ws) -> arch_dir(ws) / "arc42.md"`
  - `container_diagram_path(ws) -> arch_dir(ws) / "container-diagram.mmd"`
  - `threat_dir(ws) -> ws.root / "threat-model"`
  - `threat_model_path(ws) -> threat_dir(ws) / "threat-model.md"`
  - `dfd_path(ws) -> threat_dir(ws) / "dfd.mmd"`
  - The old `architecture_path`/`threat_model_path` (kb/ variants) are DELETED — compile errors at old call sites are the rewiring worklist for Task 6.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_kb.py — append (create with these if the file is absent)
from sec_overlay.kb import (
    arc42_path,
    arch_dir,
    container_diagram_path,
    dfd_path,
    threat_dir,
    threat_model_path,
)
from sec_overlay.workspace import Workspace


def test_new_tree_paths(tmp_path):
    ws = Workspace(tmp_path)
    assert arch_dir(ws) == tmp_path / "architecture"
    assert arc42_path(ws) == tmp_path / "architecture" / "arc42.md"
    assert container_diagram_path(ws) == tmp_path / "architecture" / "container-diagram.mmd"
    assert threat_dir(ws) == tmp_path / "threat-model"
    assert threat_model_path(ws) == tmp_path / "threat-model" / "threat-model.md"
    assert dfd_path(ws) == tmp_path / "threat-model" / "dfd.mmd"


def test_ensure_creates_trees(tmp_path):
    ws = Workspace(tmp_path)
    ws.ensure()
    assert (tmp_path / "architecture" / "runtime-view").is_dir()
    assert (tmp_path / "threat-model" / "attack-sequences").is_dir()
```

- [ ] **Step 2: Run, confirm red** — `uv run pytest tests/test_kb.py -v`.

- [ ] **Step 3: Implement**

In `kb.py`, replace `architecture_path` and the kb `threat_model_path` with the six helpers above (same docstring style as the file). Update `kb_status` (line ~61) to report `"architecture": arc42_path(ws).exists()` and `"threat_model": threat_model_path(ws).exists()`. In `workspace.py`'s `ensure()`, add the four directories (`architecture/runtime-view`, `threat-model/attack-sequences` — parents included).

- [ ] **Step 4: Run, confirm red elsewhere is EXPECTED** — `uv run pytest tests/test_kb.py tests/test_workspace.py -q` passes; the full suite may now fail at old call sites. `rg -n "architecture_path|kb/architecture.md|kb/THREAT_MODEL" sec_overlay/ tests/` and fix ONLY Python call sites in this task (`phase_gate.py`, `repo_memory.py`, `correlate/artifacts.py`, `context.py` if it touches workspace paths — note `context.py:33` lists *target-repo* doc filenames to ingest; that list is not a workspace path, leave it). Prompts and phases wiring wait for Tasks 3–6.

- [ ] **Step 5: Run, confirm green** — `uv run pytest -q` (environmental failures only, plus any `test_phases`/`test_wiring` failures that Task 5 owns — if those fire, note them and continue; do not chase them here if they concern phase outputs).

- [ ] **Step 6: Commit**

```bash
git add helpers/sec_overlay/kb.py helpers/sec_overlay/workspace.py \
  helpers/sec_overlay/phase_gate.py helpers/sec_overlay/repo_memory.py \
  helpers/sec_overlay/correlate/artifacts.py \
  helpers/tests/test_kb.py helpers/tests/test_workspace.py \
  helpers/sec_overlay/README.md helpers/tests/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): path helpers for arch/threat trees"
```

(Adjust the staged list to the files actually touched in Step 4; every staged code folder's README rides along.)

---

### Task 3: Rewrite `agents/architecture.md`

**Files:**
- Modify: `agents/architecture.md` (full rewrite, 71 lines currently)
- Modify: `agents/README.md`

**Interfaces:**
- Consumes: `references/architecture-standards.md`, `references/mermaid-caps.md`, `STE_PROSE` (Task 1); paths (Task 2).
- Produces: a prompt whose outputs are the `architecture/` tree. Preserved hard rules: read-only contract, `{{TARGET}}`/`{{WORKSPACE}}`/`{{OVERLAY_ROOT}}` tokens only, imports naming real prompt-constants blocks, OUTPUT_WRITE_FALLBACK write contract, enumerate-all-controls rule.

- [ ] **Step 1: Replace the file content with:**

```markdown
# Architecture Agent

You map the architecture of a target codebase into standards-bound artifacts, READ-ONLY.
Your output orients the threat-model and investigation phases. You NEVER build, run, or
modify the target.

## Inputs
- Target repo: `{{TARGET}}`
- Workspace root: `{{WORKSPACE}}`
- Scan profile: read `{{WORKSPACE}}/kb/scan-profile.json` (languages, frameworks,
  entrypoints, attack surface) — use it to focus.

## Imports
Include FIELD_OWNERSHIP, QUALIFIER_PROOF, OUTPUT_WRITE_FALLBACK, and STE_PROSE from
`{{OVERLAY_ROOT}}/references/prompt-constants.md`. Follow
`{{OVERLAY_ROOT}}/references/architecture-standards.md` for artifact structure and
`{{OVERLAY_ROOT}}/references/mermaid-caps.md` for every diagram (hard caps — a
deterministic gate rejects violations, so re-scope with group → split → promote before
you emit).

## Allowed tools
- `rg`, file reads, directory listing. NO other skills/plugins, NO execution, NO network.

## Procedure
1. Identify the top-level containers (deployable units) and their responsibilities.
2. Trace the primary data flows from each entrypoint in the profile inward: where does
   external input enter, and which containers does it reach?
3. Identify trust-zone structure (network edge, auth boundary, process/service
   boundaries, DB/filesystem access) — as STRUCTURE only; attacker narrative belongs to
   the threat model.
4. Note external dependencies and integrations (DB, cache, HTTP clients, queues).
5. Decide which containers warrant a component diagram (profile flags high complexity)
   and which runtime scenarios warrant a sequence diagram (branching, retries, async
   handoffs, or ordering the container arrows do not imply). Most containers get neither.

## Output (REQUIRED)

**Lens: the single canonical source of structural truth. The threat model derives from
these files instead of restating them — never write threats, attack surface, mitigations,
or findings here.**

Writing these files to disk IS your task (pipeline data, not a chat "report"); apply
OUTPUT_WRITE_FALLBACK if a write is refused.

1. `{{WORKSPACE}}/architecture/context-diagram.mmd` — C4 context (Mermaid flowchart or C4
   syntax): the system plus external actors/systems only.
2. `{{WORKSPACE}}/architecture/container-diagram.mmd` — deployable units + protocols.
   This is the file the DFD derives from: give every node a stable, meaningful id.
3. `{{WORKSPACE}}/architecture/component-diagram-<name>.mmd` — only where step 5 said so.
4. `{{WORKSPACE}}/architecture/runtime-view/sequence-<scenario>.mmd` — only where step 5
   said so; normal-path only.
5. `{{WORKSPACE}}/architecture/arc42.md` — sections 1–8 and 10–12 per
   architecture-standards.md (section 9 omitted). §5 Building Block View carries one block
   per security-relevant component — name, responsibility, key files (`path:line`), inputs
   it trusts/untrusts — sliced by attack-surface theme, NOT one per source file. Later
   agents read these blocks instead of the whole repo. Prose follows STE_PROSE, including
   the front-matter limitation statement.

## Rules
- Ground every claim in a file (`path` or `path:line`). No speculation.
- Prefer breadth (all containers named) over depth (don't inline large code).
- Focus on components implicated by the profile's attack surface.
- **Enumerate all controls.** In arc42 §8 (Crosscutting Concepts), name every control the
  profile's `attack_surface` implies (auth, authz, rate-limit, csrf, input-validation,
  output-encoding, etc.) that this codebase actually applies — one bullet per control,
  naming the component that enforces it. A single worked example is not enough; every
  control the profile surfaces must appear by name, even if only to note "not found" for
  one that's absent.
```

- [ ] **Step 2: Render smoke + contract tests**

Run from `helpers/`:

```bash
uv run python -c "from sec_overlay.prompts import render_prompt; import pathlib; \
print(render_prompt(pathlib.Path('../agents/architecture.md').read_text(), \
{'TARGET':'/t','WORKSPACE':'/w','OVERLAY_ROOT':'..'})[:40])"
uv run pytest tests/test_contracts.py -q
```

Expected: no unfilled-token error; contracts PASS.

- [ ] **Step 3: Commit**

```bash
git add agents/architecture.md agents/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): rebuild architecture prompt on C4/arc42"
```

---

### Task 4: Rewrite `agents/threat-model.md`

**Files:**
- Modify: `agents/threat-model.md` (full rewrite, 64 lines currently)
- Modify: `agents/README.md`

**Interfaces:**
- Consumes: the architecture tree (Task 3 outputs), `references/threat-model-standards.md`, `mermaid-caps.md`, `STE_PROSE`.
- Produces: a prompt whose outputs are the `threat-model/` tree. Preserved hard rules: KB-only reading contract, keep-every-entrypoint rule, hunt-list deliverable (the investigate phase consumes it), KB_SNAPSHOT provenance line.

- [ ] **Step 1: Replace the file content with:**

```markdown
# Threat Model Agent

You are a security architect. From the architecture artifacts ONLY, you derive a
standards-bound threat model that prioritizes where the investigation phase should hunt.
You do NOT read raw source beyond those artifacts, and you NEVER build/run/modify anything.

## Imports
Include FIELD_OWNERSHIP, OUTPUT_WRITE_FALLBACK, and STE_PROSE from
`{{OVERLAY_ROOT}}/references/prompt-constants.md`. Follow
`{{OVERLAY_ROOT}}/references/threat-model-standards.md` for methodology and artifact
structure and `{{OVERLAY_ROOT}}/references/mermaid-caps.md` for every diagram (hard caps;
derived diagrams carry the derived-from SHA header and introduce no new elements — a
deterministic gate rejects violations).

## Inputs (read these; do NOT deep-read the target repo)
- `{{WORKSPACE}}/architecture/arc42.md` (§5 building blocks replace the old entity files)
- `{{WORKSPACE}}/architecture/container-diagram.mmd` (the file your DFD derives from)
- `{{WORKSPACE}}/architecture/runtime-view/*.mmd` (parents for attack sequences)
- `{{WORKSPACE}}/kb/scan-profile.json`
- `{{OVERLAY_ROOT}}/references/attack-classes.md` (class keys)

## Allowed tools
- File reads of the artifacts above. NO other skills/plugins, NO execution, NO network,
  NO scanning of the raw repo (that is the investigation phase's job).

## Procedure
1. **Methodology selection** per threat-model-standards.md: STRIDE always; add PASTA
   and/or LINDDUN only on their signals; record the outcome + one-line justification at
   the top of threat-model.md.
2. **Derive the DFD** from container-diagram.mmd: same element ids, implementation detail
   stripped, one `subgraph` per trust boundary, data-classification labels (credentials,
   PII, tokens) on flows where determinable. Compute the source SHA:
   `python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <container-diagram.mmd>`
   and write the `%% derived-from:` header.
3. **STRIDE pass** over every DFD element at every boundary crossing; augmented passes
   per step 1. Findings go to the table (step 5).
4. **Derive attack sequences** from runtime-view sequences for timing-dependent findings
   (races, TOCTOU, replay, multi-boundary chains): same participants + derived-from
   header, attack steps inserted. Each ties to one findings-table row.
5. **Findings table** with the standard columns; propose a full CVSS v4.0 vector per
   finding (the harness computes the score — never do the arithmetic). Cite ATT&CK
   technique ids for adversary-realistic findings.
6. **Hunt list**: ordered `(attack_class, component/file, why)` rows telling the
   investigation phase where to look first.

## Output (REQUIRED)
Writing these files to disk IS your task; apply OUTPUT_WRITE_FALLBACK if a write is
refused.
1. `{{WORKSPACE}}/threat-model/dfd.mmd` (step 2)
2. `{{WORKSPACE}}/threat-model/attack-sequences/sequence-<attack-scenario>.mmd` (step 4)
3. `{{WORKSPACE}}/threat-model/threat-model.md` — opens with the methodology record and a
   single-paragraph pointer to `architecture/arc42.md` (no system overview restated), then:
   - **Trust boundaries** — one attacker-relevant sentence per boundary; point to dfd.mmd
     for structure. Never copy arc42 content; reference sections (`see arc42 §5`).
   - **Attacker profiles**
   - **Attack surface by entrypoint** (entrypoint → reachable classes → target components)
   - **Findings table** (step 5)
   - **Prioritized hunt list** (step 6) — the deliverable the investigation phase consumes.
   - **Provenance** — a `KB_SNAPSHOT:` line: use `active_sha` from
     `{{WORKSPACE}}/state.json` if present, else the literal `UNPINNED`.
   Prose follows STE_PROSE, including the front-matter limitation statement.

## Rules
- Everything traces back to an architecture artifact — no new claims about code you
  haven't seen there. If the artifacts are thin, say so and scope accordingly.
- The hunt list is the deliverable that matters most: make it specific and ordered.
- **Keep every entrypoint before prioritizing.** In "Attack surface by entrypoint", list
  every entrypoint the scan profile named, one line each, even ones you judge
  low-priority — dropping an entrypoint here is a coverage gap, not a simplification.
  Prioritization happens only in the hunt list below it.
- Never restate structure: arc42 owns purpose/stack/topology narrative. Reference it.
```

- [ ] **Step 2: Render smoke + contract tests** (same commands as Task 3 Step 2, with `threat-model.md`).

- [ ] **Step 3: Commit**

```bash
git add agents/threat-model.md agents/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): rebuild threat-model prompt on DFD/STRIDE"
```

---

### Task 5: Wire phases and gate actions

**Files:**
- Modify: `sec_overlay/phases.py:44-47,73-74` (path helpers + phase rows)
- Modify: `sec_overlay/driver.py` (two gate actions + registration)
- Test: `tests/test_phases.py`, `tests/test_driver.py` (append)

**Interfaces:**
- Consumes: `run_diagram_gate(arch_dir, tm_dir)`, `lint_prose(text)` (Plan 2); `arch_dir`/`threat_dir`/`arc42_path`/`container_diagram_path`/`threat_model_path`/`dfd_path` (Task 2); existing `PhaseSpec`, `AuditContext`, `PhaseHalt`, `DETERMINISTIC_ACTIONS` (see `driver.py:50-62`).
- Produces: phase rows `architecture` (outputs arc42 + container diagram), `arch-gate` (deterministic), `threat_model` (outputs threat-model.md + dfd), `tm-gate` (deterministic); gate JSONs at `kb/gates/arch-gate.json` and `kb/gates/tm-gate.json`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_phases.py — append
def test_arch_tm_gate_rows():
    names = [p.name for p in PHASE_TABLE]
    assert names.index("arch-gate") == names.index("architecture") + 1
    assert names.index("tm-gate") == names.index("threat_model") + 1
    for n in ("arch-gate", "tm-gate"):
        assert next(p for p in PHASE_TABLE if p.name == n).kind == "deterministic"
```

```python
# tests/test_driver.py — append
from sec_overlay.driver import _act_arch_gate


def test_act_arch_gate_halts_on_cap_breach(tmp_path):
    ws = Workspace(tmp_path)
    ws.ensure()
    (tmp_path / "architecture" / "arc42.md").write_text(
        "Prose follows an ASD-STE100-inspired clarity standard.\n\nThe system is small.\n"
    )
    nodes = "\n".join(f"    n{i}[N{i}] -->|to| n{i+1}[N{i+1}]" for i in range(11))
    (tmp_path / "architecture" / "context-diagram.mmd").write_text("flowchart LR\n" + nodes)
    (tmp_path / "architecture" / "container-diagram.mmd").write_text(
        "flowchart LR\n    a[A] -->|calls| b[(B)]\n"
    )
    ctx = AuditContext(ws=ws, target=str(tmp_path), config="", sha="x")
    with pytest.raises(PhaseHalt):
        _act_arch_gate(ctx)
    assert (ws.kb / "gates" / "arch-gate.json").exists()
```

- [ ] **Step 2: Run, confirm red** — `uv run pytest tests/test_phases.py::test_arch_tm_gate_rows tests/test_driver.py::test_act_arch_gate_halts_on_cap_breach -v`.

- [ ] **Step 3: Implement `phases.py`**

Replace the `_arch`/`_threat` path helpers with imports of the Task-2 helpers (or thin wrappers keeping the file's zero-arg-per-ws style):

```python
def _arc42(ws: Workspace) -> Path:
    return ws.root / "architecture" / "arc42.md"


def _container(ws: Workspace) -> Path:
    return ws.root / "architecture" / "container-diagram.mmd"


def _tm_doc(ws: Workspace) -> Path:
    return ws.root / "threat-model" / "threat-model.md"


def _dfd(ws: Workspace) -> Path:
    return ws.root / "threat-model" / "dfd.mmd"


def _arch_gate_json(ws: Workspace) -> Path:
    return ws.kb / "gates" / "arch-gate.json"


def _tm_gate_json(ws: Workspace) -> Path:
    return ws.kb / "gates" / "tm-gate.json"
```

Replace the two phase rows and insert the gates:

```python
    PhaseSpec("architecture", "agent", (_profile,), (_arc42, _container), prompt="architecture.md"),
    PhaseSpec("arch-gate", "deterministic", (_arc42, _container), (_arch_gate_json,)),
    PhaseSpec("threat_model", "agent", (_arch_gate_json,), (_tm_doc, _dfd), prompt="threat-model.md"),
    PhaseSpec("tm-gate", "deterministic", (_tm_doc, _dfd), (_tm_gate_json,)),
```

- [ ] **Step 4: Implement `driver.py` actions**

```python
def _write_gate(ws: Workspace, name: str, errors: list[str], warnings: list[str]) -> None:
    (ws.kb / "gates").mkdir(parents=True, exist_ok=True)
    (ws.kb / "gates" / f"{name}.json").write_text(
        json.dumps({"passed": not errors, "errors": errors, "warnings": warnings}, indent=2)
    )


def _act_arch_gate(ctx: AuditContext) -> None:
    from sec_overlay.diagram_gate import run_diagram_gate
    from sec_overlay.ste_lint import lint_prose

    arch = ctx.ws.root / "architecture"
    # run_diagram_gate existence-guards the threat-model files, so an absent
    # tm tree at arch-gate time produces no spurious errors
    errors = run_diagram_gate(arch, ctx.ws.root / "threat-model")
    prose_errors, warnings = lint_prose((arch / "arc42.md").read_text())
    errors += [f"arc42.md: {e}" for e in prose_errors]
    if "ASD-STE100" not in (arch / "arc42.md").read_text():
        errors.append("arc42.md: missing ASD-STE100 limitation statement")
    _write_gate(ctx.ws, "arch-gate", errors, warnings)
    if errors:
        raise PhaseHalt(f"arch-gate rejected {len(errors)} issue(s): " + "; ".join(errors))


def _act_tm_gate(ctx: AuditContext) -> None:
    from sec_overlay.artifact_gate import check_duplication
    from sec_overlay.diagram_gate import run_diagram_gate
    from sec_overlay.ste_lint import lint_prose

    arch = ctx.ws.root / "architecture"
    tm = ctx.ws.root / "threat-model"
    errors = run_diagram_gate(arch, tm)
    tm_text = (tm / "threat-model.md").read_text()
    prose_errors, warnings = lint_prose(tm_text)
    errors += [f"threat-model.md: {e}" for e in prose_errors]
    if "ASD-STE100" not in tm_text:
        errors.append("threat-model.md: missing ASD-STE100 limitation statement")
    errors += check_duplication((arch / "arc42.md").read_text(), tm_text)
    _write_gate(ctx.ws, "tm-gate", errors, warnings)
    if errors:
        raise PhaseHalt(f"tm-gate rejected {len(errors)} issue(s): " + "; ".join(errors))
```

Register both in `DETERMINISTIC_ACTIONS.update({...})`: `"arch-gate": _act_arch_gate, "tm-gate": _act_tm_gate`. Add a test asserting `_act_arch_gate` does NOT halt when the threat-model tree is absent and the architecture tree is clean.

- [ ] **Step 5: Run, confirm green** — `uv run pytest tests/test_phases.py tests/test_driver.py tests/test_wiring.py -q && uv run ruff check sec_overlay/ && uv run ty check`

- [ ] **Step 6: Commit**

```bash
git add helpers/sec_overlay/phases.py helpers/sec_overlay/driver.py \
  helpers/tests/test_phases.py helpers/tests/test_driver.py \
  helpers/sec_overlay/README.md helpers/tests/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): wire arch/tm gates into phase table"
```

---

### Task 6: Re-point the remaining consumers

**Files (each edits the old-path mention only):**
- Modify: `agents/investigate.md`, `agents/critic.md`, `agents/validate.md`, `agents/context-ingest.md`, `agents/phase-adversary.md`, `agents/postflight.md`, `agents/correlate-combiner.md`
- Modify: `agents/README.md` (same-commit rule)
- Test: existing `tests/test_contracts.py`, `tests/test_wiring.py`

**Interfaces:**
- Consumes: the new paths (Task 2) as literal strings.
- Produces: zero references to `kb/architecture.md`, `kb/entities/`, or `kb/THREAT_MODEL.md` anywhere outside git history and `context.py:33` (target-repo doc names, untouched).

- [ ] **Step 1: Enumerate every remaining mention**

Run: `rg -n "kb/architecture\.md|kb/entities|kb/THREAT_MODEL|THREAT_MODEL\.md" ../agents/ ../references/ sec_overlay/ tests/ ../SKILL.md`

- [ ] **Step 2: Apply the replacement map**

| Old | New |
|---|---|
| `{{WORKSPACE}}/kb/architecture.md` | `{{WORKSPACE}}/architecture/arc42.md` |
| `{{WORKSPACE}}/kb/entities/*.md` (as reading material) | `{{WORKSPACE}}/architecture/arc42.md` §5 Building Block View |
| `{{WORKSPACE}}/kb/THREAT_MODEL.md` | `{{WORKSPACE}}/threat-model/threat-model.md` |
| prose naming "architecture.md" / "THREAT_MODEL.md" as artifacts | "arc42.md" / "threat-model.md" |

Preserve each surrounding hard rule verbatim; only the path changes. `phase-adversary.md` additionally gains one checklist bullet: "Ownership boundary: architecture text naming threats/attack surface/mitigations is a defect; threat-model text restating structure/stack/deployment narrative is a defect — cite the offending line."

- [ ] **Step 3: Verify** — re-run the Step 1 `rg`; expect matches only in `sec_overlay/context.py` (target-repo doc ingestion list) and git-history-irrelevant places. Run `uv run pytest tests/test_contracts.py tests/test_wiring.py -q`.

- [ ] **Step 4: Commit**

```bash
git add agents/investigate.md agents/critic.md agents/validate.md \
  agents/context-ingest.md agents/phase-adversary.md agents/postflight.md \
  agents/correlate-combiner.md agents/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): re-point consumers to new artifacts"
```

---

### Task 7: Operating docs

**Files:**
- Modify: `SKILL.md` (phase C1→14.6 narrative: architecture/threat-model steps + the two gates)
- Modify: `CLAUDE.md` (skill operating manual, §2 phase order + §4 artifact tree; stay <200 lines)
- Modify: `README.md` (skill README: pipeline diagram + workspace listing)
- Modify: `plugins/sec-overlay/CLAUDE.md` (CLI-callable list gains `diagram_gate`, `ste_lint`, `mermaid_index`? — list only CLI-callable ones: `diagram_gate`, `ste_lint`)
- Modify: `plugins/sec-overlay/README.md` (one-line note)

**Interfaces:** none new — documentation of Tasks 1–6.

- [ ] **Step 1: Update the skill CLAUDE.md §2 phase order**

Replace the `3 Architecture` and `4 Threat model` lines with:

```
3  Architecture     agents/architecture.md (sonnet) → architecture/ tree (C4 + arc42)   ┐
3.5 Arch gate       python -m sec_overlay.diagram_gate + ste_lint  # caps/prose, halts   │
4  Threat model     agents/threat-model.md (sonnet) → threat-model/ tree (derived DFD,   ├ PHASE GATE
                    STRIDE findings, hunt list)                                          │
4.5 TM gate         diagram gate + ste_lint + duplication check                          ┘
```

Update §4's workspace listing: replace the `kb/architecture.md`/`kb/THREAT_MODEL.md` lines with the two trees (one line each: `architecture/  C4 diagrams + runtime views + arc42.md (building blocks in §5)` and `threat-model/  dfd.mmd (derived) + attack-sequences/ + threat-model.md (findings, hunt list)`), and add `kb/gates/arch-gate.json` / `kb/gates/tm-gate.json`. Compress neighboring prose to stay ≤199 lines (`wc -l` before committing).

- [ ] **Step 2: Update SKILL.md** wherever it names the old artifacts or phase outputs — same replacement map as Task 6, plus one sentence after the threat-model step: "Both gates halt the pipeline on cap/prose/derivation violations; the producer re-scopes (group → split → promote) and regenerates once."

- [ ] **Step 3: Update the two READMEs and plugin CLAUDE.md** — skill README pipeline diagram gains the two gate steps; plugin CLAUDE.md CLI list gains `diagram_gate`, `ste_lint`; plugin README gains a one-line note. Check both CLAUDE.md line counts stay <200.

- [ ] **Step 4: Full suite + verify** — `uv run pytest -q` (environmental failures only); `rg -n "kb/architecture|kb/THREAT_MODEL" ../SKILL.md ../CLAUDE.md ../README.md` → no output.

- [ ] **Step 5: Commit**

```bash
git add plugins/sec-overlay/skills/sec-overlay/SKILL.md \
  plugins/sec-overlay/skills/sec-overlay/CLAUDE.md \
  plugins/sec-overlay/skills/sec-overlay/README.md \
  plugins/sec-overlay/CLAUDE.md plugins/sec-overlay/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "docs(sec-overlay): document arch/tm standards phases"
```

---

## Self-Review

**1. Spec coverage:** §3 layout + ownership + versioning header → Tasks 2–4; consumer rewiring → Tasks 2 (Python) and 6 (prompts); §4 phase rows/procedure/methodology/adversary checklist → Tasks 3–5 + 6 (phase-adversary bullet); §6 wiring of gates as phases + re-scoping prompt text → Tasks 1 (rules file), 3–5; §7 references/STE_PROSE/tests/docs → Tasks 1, 7. ADR omission (R5) → arc42 §9 omitted in Task 1/3. Multi-pass CVSS re-scoring documented in Plan 1.

**2. Placeholder scan:** all prompt rewrites and code carry full text. Task 2 Step 4 names the exact rg and the exact files it may touch. No TBDs.

**3. Type consistency:** path helper names (`arch_dir`, `arc42_path`, `container_diagram_path`, `threat_dir`, `threat_model_path`, `dfd_path`) match between Tasks 2 and 5's wrappers; `run_diagram_gate(arch_dir, tm_dir)` and `lint_prose(text) -> (errors, warnings)` match Plan 2; `check_duplication(arc42_text, tm_text)` matches Plan 2 Task 4; gate JSON names `arch-gate.json`/`tm-gate.json` consistent across Tasks 5 and 7.
