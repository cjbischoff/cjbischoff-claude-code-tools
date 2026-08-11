# sec-overlay Documentation Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove stale Go-rewrite prose from the sec-overlay docs, bring the READMEs and skill CLAUDE.md in line with how this fork actually works, add per-folder READMEs, and extend the pre-commit hook to keep folder READMEs fresh.

**Architecture:** Documentation-only, except one Bash hook change. Six grouped commits, each self-contained and independently reviewable. Each commit carries its own `README.md` + `CHANGELOG.md` (+ affected folder README) updates, per repo governance.

**Tech Stack:** Markdown, Mermaid, Bash (`scripts/hooks/pre-commit-check.sh`), `shellcheck`/`shfmt` for the hook, `git` for the hook test harness. No Python behavior changes.

## Global Constraints

Copied verbatim from the spec and the workspace CLAUDE.md. Every task's requirements implicitly include this section.

- Work on branch `docs/sec-overlay-doc-overhaul`; never commit to `main` (a hook blocks it).
- Conventional Commits; summary under 50 chars; body wrapped at 72.
- Every commit that changes a tracked file updates `README.md` and adds a `CHANGELOG.md` entry in the **same commit**.
- A commit that changes a tracked file inside a folder that has a `README.md` updates that folder's `README.md` in the **same commit** (Directory-Guide folders `plugins/` and `scripts/` are already enforced; Task 6 generalizes this).
- No `Co-Authored-By` trailer. No `--no-verify`. No `git add -A` / `git add .` / `git commit -a` — stage explicit paths.
- Do **not** bump any plugin `version` field (the user bumps it manually on release).
- Scripts must not reference paths outside their plugin directory.
- Name normalization everywhere — use only these identifiers: `sec_overlay` (Python package), `sec-overlay` (distribution / plugin / skill), `$SEC_OVERLAY_HOME`, `.sec-overlay` (sidecar), `{{OVERLAY_ROOT}}` / `${CLAUDE_PLUGIN_ROOT}` (run-path token). No `sec_harness` / `sec-harness` / `$SEC_HARNESS_HOME` / `.sec-harness` / `HARNESS_ROOT` remnants.

## Verified facts (measured 2026-08-11, use these exact values)

- Test baseline from `plugins/sec-overlay/skills/sec-overlay/helpers/`: **575 tests, 573 pass, 2 env-only failures**.
- The 2 env-only failures are exactly:
  - `tests/test_bench.py::test_seed_corpus_is_valid` — gitignored bench corpus absent.
  - `tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` — excluded semgrep submodule.
- **78** test files in `helpers/tests/`.
- The finding serialization/schema contract is enforced by `helpers/tests/test_contracts.py` and `helpers/tests/test_finding_schema.py` against `references/finding.schema.json`. These replace every "frozen contract with the Go port" claim.
- No Go port exists in this fork: no `go/`, no `gen_golden.py`, no `TestParity`.
- Folder file counts (for Task 5): `agents/classes` 11, `references/asvs` 1, `references/codeguard` 7, `references/hunting` 8, `helpers/sec_overlay` 71, `helpers/tests` 78.

## Deviations from the approved spec (with reasons)

Three refinements were discovered while mapping the files. They shrink or retarget work; none add scope.

1. **CLAUDE.md is surgical, not a full rewrite (spec §3).** The user decided (post-approval): keep the audit operating manual (§0 Mission, §2 Environment, §3 Run audit, §4 Signal-over-noise, §5 Artifacts, §6 References, §7 Developing); **replace** §1 (Go) with a real git/governance section; **fix** the §2/§7 failure count; **rewrite** §8 to the real hook mechanism. Task 3 reflects this.
2. **The skill overview README already exists (spec §4).** `skills/sec-overlay/README.md` already contains the four invariants, both Mermaid diagrams, the worked SQLi example, how-to-run, and the output-workspace layout. Task 4 is therefore *edit-and-verify* (strip 3 stale references, fix one count, and check the existing diagrams/example against current code), not author-from-scratch.
3. **The hook test is Bash, not pytest (spec §6).** There is no Python environment at the repo root (Python lives only under `helpers/`, and repo-level scripts must not reach into the plugin). Task 6 uses a colocated Bash test (`scripts/hooks/test-pre-commit-check.sh`) that drives the hook inside throwaway git repos and asserts exit codes — red first, then green.

---

## Task 1: Remove Go-rewrite prose from the four live docs

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md` (Go references only — the §8 rewrite and count fix are Task 3)
- Modify: `plugins/sec-overlay/skills/sec-overlay/README.md` (Go references only — the count fix is Task 4)
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md` (Go references only — the count fixes are Task 4/4-scope; the "frozen contract" heading and block here are Go, so they belong to this task)
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/README.md`
- Modify (governance): `README.md`, `CHANGELOG.md`
- Modify (folder README, because helpers/ and references/ change): none beyond the four docs above — each edited file *is* its folder's README, which satisfies the folder-README rule for that folder.

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: a "finding serialization/schema contract" phrasing that Tasks 3 and 4 reuse verbatim: *"`models.py` and `evidence.py` define the finding serialization/schema contract; changing a field means updating `references/finding.schema.json` and keeping `test_contracts.py` and `test_finding_schema.py` green."*

- [ ] **Step 1: Scrub `CLAUDE.md` intro line 5**

Replace:
```
against real codebases, and (2) maintaining the skill **without breaking the parallel Go conversion**.
```
with:
```
against real codebases, and (2) maintaining the skill and its documentation.
```

- [ ] **Step 2: Delete the entire §1 "Git — protecting the parallel Go conversion" section**

Delete lines 33–68 (the `## 1. Git — protecting the parallel Go conversion (READ FIRST)` heading through the end of "Prefer to avoid touching these two files at all while the conversion is in flight.", including the `### The one coupling point — the JSON contract` subsection and the trailing `---`). Task 3 inserts the replacement §1 (git/governance). For this task, remove the Go content; leave a single `---` separator where the section was so the document still parses.

- [ ] **Step 3: Scrub the `BinaryAdapter` Go sentence in §7**

In the `helpers/bench/` bullet (around line 299–302), delete only the final sentence:
```
Its
  `BinaryAdapter` is the seam that will regression-test the Go binary against this Python contract.
```
Keep the rest of the bullet (the bench description and the `python -m bench.run …` command).

- [ ] **Step 4: Scrub the `helpers/README.md` §8 table row Go phrase in `CLAUDE.md`**

In the §8 documentation table (around line 322), change the `helpers/README.md` row cell:
```
the ~70 Python modules grouped by job, the CLI-callable list, the deterministic pipeline diagram, the two frozen contracts, and the two in-code invariants.
```
to:
```
the ~70 Python modules grouped by job, the CLI-callable list, the deterministic pipeline diagram, the finding serialization/schema contract, and the two in-code invariants.
```
(The rest of §8 — the hook mechanism — is rewritten in Task 3.)

- [ ] **Step 5: Scrub `skills/sec-overlay/README.md` line 18**

Change the CLAUDE.md pointer row:
```
| Git protocol, the Go-port contract, environment setup | [`CLAUDE.md`](CLAUDE.md) |
```
to:
```
| Git protocol, environment setup, developing the skill | [`CLAUDE.md`](CLAUDE.md) |
```

- [ ] **Step 6: Replace the "Two coupling points" block in `skills/sec-overlay/README.md`**

Replace lines 240–247 (from `Two coupling points to respect before editing:` through the end of the Docs-track-code bullet) with:
```
One coupling point to respect before editing:

- **The finding contract.** `helpers/sec_overlay/models.py` and `evidence.py` define the finding
  serialization/schema. Change a field and you must update `references/finding.schema.json` and keep
  `helpers/tests/test_contracts.py` and `helpers/tests/test_finding_schema.py` green.
- **Docs track code.** When you change anything in `agents/`, `helpers/`, or `references/`,
  update that folder's README in the **same commit**. A pre-commit hook enforces this — see
  [`CLAUDE.md`](CLAUDE.md) §8.
```
(The "~470 tests / 3 env-only failures" count on line 235 is fixed in Task 4.)

- [ ] **Step 7: Replace the "frozen contract" heading and blockquote in `helpers/README.md`**

Change the section heading (line 92):
```
### Data model & serialization — the frozen contract
```
to:
```
### Data model & serialization — the finding contract
```
Then replace the blockquote (lines 99–101):
```
> **These two (`models.py`, `evidence.py`) are frozen contracts with the Go port.** The Go
> binary asserts byte-for-byte parity against goldens generated from them. Changing a field
> or the `_MECHANICAL` set breaks the Go build. See skill [`CLAUDE.md`](../CLAUDE.md) §1.
```
with:
```
> **These two (`models.py`, `evidence.py`) define the finding serialization/schema contract.**
> Change a `Finding`/`CampaignState` field or the `_MECHANICAL` set and you must update
> `../references/finding.schema.json` and keep `tests/test_contracts.py` and
> `tests/test_finding_schema.py` green.
```
(The "~75 files, ~470 tests / 3 env-only failures" counts elsewhere in this file are fixed in Task 4.)

- [ ] **Step 8: Scrub the Go parenthetical in `references/README.md`**

Change lines 213–215:
```
  in tests and gates. A field you add here must be added to `models.py` too, or the gate
  rejects real findings. (`models.py` is additionally a *frozen contract* with the Go port —
  see the skill [`CLAUDE.md`](../CLAUDE.md).)
```
to:
```
  in tests and gates. A field you add here must be added to `models.py` too, or the gate
  rejects real findings, and `test_contracts.py` / `test_finding_schema.py` must stay green.
```

- [ ] **Step 9: Verify no Go references remain in the live docs**

Run:
```bash
cd plugins/sec-overlay/skills/sec-overlay
rg -n -i 'go port|go rewrite|go conversion|go binary|byte-for-byte|gen_golden|TestParity|parallel Go|/go\b|core\.hooksPath|\.githooks|--no-verify' \
  CLAUDE.md README.md helpers/README.md references/README.md
```
Expected: **no matches** except any inside Task 3's not-yet-written §8 (which this task leaves stubbed). If `core.hooksPath` / `.githooks` / `--no-verify` still match, they are in CLAUDE.md §8 and are handled in Task 3 — note them and proceed. Any `go`/`byte-for-byte`/`TestParity` match is a Task-1 miss; fix it.

- [ ] **Step 10: Update governance docs and commit**

Update root `README.md` (Status: replace the running per-task log with a short current-state summary is deferred to Task 2; for this commit add a one-line Status entry: "Removed stale Go-rewrite prose from the four live sec-overlay docs.") and add a `CHANGELOG.md` entry under `### Removed`:
```
- Remove stale Go-rewrite prose from the four live sec-overlay docs.
```
Then stage explicit paths and commit:
```bash
git add plugins/sec-overlay/skills/sec-overlay/CLAUDE.md \
        plugins/sec-overlay/skills/sec-overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        README.md CHANGELOG.md
git commit -m "docs(sec-overlay): remove Go-rewrite prose"
```
Expected: hook passes (README + CHANGELOG staged; each edited doc is its own folder README).

---

## Task 2: Rewrite the root marketplace README to the template

**Files:**
- Modify: `README.md`
- Modify (governance): `CHANGELOG.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the canonical root README shape other contributors follow.

- [ ] **Step 1: Rewrite `README.md`**

Keep the Directory Guide, Artifact inventory, and Decisions sections (they carry governance meaning). Fold the template's Installation/Plugins/Development/Governance/License sections in, and collapse the running per-task Status log to a short current-state summary. Target content:

```markdown
# cjbischoff-claude-code-tools

Claude Code plugin marketplace — personal plugins for Christopher Bischoff.

## Installation

```
/plugin marketplace add cjbischoff/cjbischoff-claude-code-tools
/plugin install sec-overlay@cjbischoff-claude-code-tools
```

## Plugins

- **sec-overlay**: agentic security-audit harness (static analysis, tool-receipt gate).

## Development

```bash
claude plugin validate .      # validate plugin + marketplace manifests
prek run                      # run governance hooks
cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q   # Python core tests
```

## Directory Guide

Each folder below has its own README.md describing what it holds, its naming convention, and who writes to it. A commit that changes a tracked file inside a folder that has a README.md must update that folder's README.md in the same commit.

| Folder | Purpose |
|--------|---------|
| `plugins/` | One directory per distributed plugin |
| `scripts/` | Repo-level tooling (git hook scripts) |
| `docs/` | Design specs and planning documents |

## Artifact inventory

| Path | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace manifest; lists all plugins |
| `plugins/sec-overlay/.claude-plugin/plugin.json` | sec-overlay plugin manifest |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Skill playbook: agentic security-audit harness |
| `plugins/sec-overlay/skills/sec-overlay/helpers/` | Python core (`sec_overlay` package) that runs tools and enforces gates |
| `plugins/sec-overlay/skills/sec-overlay/agents/` | LLM subagent prompts for the investigate/validate/patch phases |
| `docs/` | Design specs and implementation plans (see `docs/README.md`) |
| `.pre-commit-config.yaml` | prek hook config: doc-update guard + commit message check |
| `scripts/hooks/` | Hook scripts that enforce commit governance |
| `CHANGELOG.md` | Common Changelog; one entry per functionality commit |

## Governance

- Direct commits to `main` are blocked by a pre-commit hook; work on a `<type>/<short-kebab-description>` branch.
- Conventional Commits; summary under 50 chars; body wrapped at 72.
- Every commit that changes tracked files updates `README.md` and `CHANGELOG.md` in the same commit, plus the affected folder's `README.md`. Hooks enforce this.
- Run `prek install` once after cloning to activate the hooks.

## Status

sec-overlay is ported and green (573 pass, 2 env-only failures); plugin and marketplace manifests validate. Version stays at 0.1.0 until the user approves a bump. Pending user approval to merge the completed feature branches into `main`.

## Decisions

- plugin.json declares no components; the default `skills/` directory scan handles discovery, strict mode stays at its default (true).
- Version stays at 0.1.0 until the user approves a bump.
- Governance is enforced with prek local hooks rather than convention only, per user request for forced updates.

## License

MIT
```

- [ ] **Step 2: Verify the README renders and has no stale identifiers**

Run:
```bash
rg -n -i 'sec[_-]harness|SEC_HARNESS|docs/gsd|docs/dogfooding|documentation site|GITHUB_PAGES' README.md
```
Expected: no matches. Confirm the fenced code blocks are balanced (the nested ```` ``` ```` inside the Installation/Development sections must render — use indented view or a Markdown preview to sanity-check).

- [ ] **Step 3: Update CHANGELOG and commit**

Add a `CHANGELOG.md` entry under `### Changed`:
```
- Rewrite the root README to the marketplace template (Installation, Plugins, Development, Governance, License) and collapse the per-task Status log.
```
Commit:
```bash
git add README.md CHANGELOG.md
git commit -m "docs: rewrite root README to template"
```

---

## Task 3: Refocus the skill CLAUDE.md (surgical)

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md`
- Modify (governance): `README.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 left §1 as a bare `---` stub and left §8's hook mechanism intact (still Go/`.githooks`). This task fills §1 and rewrites §8.
- Produces: the real git-governance section and the real hook-mechanism section that Task 6's governance-doc note points at.

- [ ] **Step 1: Insert the new §1 (git & governance) where the old Go section was**

Replace the Task-1 stub (the lone `---` between §0 and §2) with:
```markdown
## 1. Git & governance (READ FIRST)

This skill lives inside the `cjbischoff-claude-code-tools` marketplace, which enforces commit
governance with prek hooks. The rules that bind every change here:

- **Branch, never `main`.** Work on `<type>/<short-kebab-description>` (e.g.
  `docs/sec-overlay-doc-overhaul`). A pre-commit hook blocks direct commits to `main`.
- **Conventional Commits.** `<type>(<scope>): <summary>`, summary under 50 chars, body wrapped
  at 72. Types: `feat` · `fix` · `chore` · `docs` · `style` · `refactor` · `perf` · `test`.
- **Docs move with code, in the same commit.** Every commit that changes a tracked file updates
  the root `README.md` and adds a `CHANGELOG.md` entry, and updates the `README.md` of any folder
  whose files changed (see §8). The hook rejects a commit that skips these.
- **Stage explicit paths.** Never `git add -A` / `git add .` / `git commit -a`. Never
  `--no-verify`.
- **Tests are required for scripts.** New or changed executable logic ships with a test in the
  same change (Python under `helpers/tests/`; shell scripts get a colocated invocation test).
- **Do not bump the plugin `version`.** The user bumps it manually on release so update
  detection works.

Merge a branch to `main` only after the user approves.

---
```

- [ ] **Step 2: Fix the env-only failure count in §2 and §7**

In §2, reconcile the failure enumeration to the measured baseline of **2** env-only failures. Change the closing sentence (around line 91–93):
```
These three failing tests are **environmental** (missing submodule / gitignored seed data), not code
defects — do not "fix" them by committing the submodule contents or fabricating seed data.
```
to:
```
The two env-only failures on a clean checkout are **environmental**, not code defects — do not
"fix" them by committing the submodule contents or fabricating seed data:
`tests/test_bench.py::test_seed_corpus_is_valid` (gitignored bench corpus) and
`tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` (excluded semgrep
submodule).
```
In §7, change the pytest comment (line 284):
```
uv run pytest -q                                   # full suite (3 env-only failures — see §2)
```
to:
```
uv run pytest -q                                   # full suite (2 env-only failures — see §2)
```

- [ ] **Step 3: Verify the count change against reality**

Run and confirm the numbers match the doc:
```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q 2>&1 | tail -1
```
Expected: `2 failed, 573 passed`. If the counts differ, update the doc to the actual output — do not assert a number you did not observe.

- [ ] **Step 4: Rewrite §8 to the real hook mechanism**

Replace the §8 body from the paragraph after the documentation table (starting `**Hard rule — docs track code in the same commit.**`, around line 325) through the end of the file's caution blockquote (line 341) with:
```markdown
**Hard rule — docs track code in the same commit.** When you change anything under `agents/`,
`helpers/`, or `references/` (or any folder that has a `README.md`), update that folder's
`README.md` in the **same commit**.

This is enforced repo-wide by the marketplace's prek pre-commit hook
(`scripts/hooks/pre-commit-check.sh`, wired in `.pre-commit-config.yaml`): for every staged file
whose folder contains a tracked `README.md`, that `README.md` must also be staged, or the commit
is rejected with the folder named. Activate the hooks once per clone with `prek install`.

Do **not** bypass with `--no-verify`. A genuinely doc-neutral change still updates the folder
README (a one-line note is enough) — the rule has no exception.
```
Leave the §8 documentation table (the four-row README table) unchanged except for the Task-1 wording fix already applied.

- [ ] **Step 5: Verify no stale hook/Go references remain anywhere in CLAUDE.md**

Run:
```bash
rg -n -i 'go port|byte-for-byte|gen_golden|TestParity|core\.hooksPath|\.githooks|--no-verify|3 env-only|three failing' \
  plugins/sec-overlay/skills/sec-overlay/CLAUDE.md
```
Expected: no matches.

- [ ] **Step 6: Update governance docs and commit**

Add a `CHANGELOG.md` entry under `### Changed`:
```
- Refocus the sec-overlay skill CLAUDE.md on repo mechanics: real git/governance section, the correct 2 env-only failure count, and the prek folder-README hook.
```
Add a root `README.md` Status line: "Refocused the sec-overlay skill CLAUDE.md on repo mechanics (git/governance, testing, hook)." Commit:
```bash
git add plugins/sec-overlay/skills/sec-overlay/CLAUDE.md README.md CHANGELOG.md
git commit -m "docs(sec-overlay): refocus skill CLAUDE.md"
```

---

## Task 4: Fix the skill overview README (counts + diagram/example verification)

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/README.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md` (the remaining count fixes)
- Modify (governance): `README.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 already stripped the Go references from both files. This task only fixes the stale test counts and verifies the diagrams/example.
- Produces: nothing downstream.

- [ ] **Step 1: Fix the count in `skills/sec-overlay/README.md`**

Change line 235:
```
uv run pytest -q          # ~470 tests (3 env-only failures — see CLAUDE.md §2)
```
to:
```
uv run pytest -q          # 575 tests (2 env-only failures — see CLAUDE.md §2)
```

- [ ] **Step 2: Fix the counts in `helpers/README.md`**

Apply these exact replacements:
- Line 24: `│   tests/                    ~75 pytest files (~470 tests)` → `│   tests/                    78 pytest files (575 tests)` (preserve the tree-diagram alignment/spacing).
- Line 36: `uv run pytest -q                                 # full suite (3 env-only failures — see skill CLAUDE.md §2)` → `# full suite (2 env-only failures — see skill CLAUDE.md §2)` (keep the command and column alignment).
- Line 188: `The `tests/` folder houses ~75 files, ~470 tests.` → `The `tests/` folder houses 78 files, 575 tests.`
- Line 278: `- **`tests/`** — ~75 files, ~470 tests, deterministic.` → `- **`tests/`** — 78 files, 575 tests, deterministic.`
- Lines 282–283: `Three failures on a clean checkout are\n  *environmental* (missing semgrep submodule, gitignored bench corpus)` → `Two failures on a clean checkout are\n  *environmental* (gitignored bench corpus, excluded semgrep submodule)`

- [ ] **Step 3: Verify both Mermaid diagrams in the overview README are consistent with the code**

The two diagrams in `skills/sec-overlay/README.md` (architecture flowchart, lines 47–73; pipeline flowchart, lines 92–110) are hand-authored. Check them against the current pipeline order in `CLAUDE.md` §3 "Phase order (one pass)" and against `helpers/README.md`'s pipeline diagram. Confirm every phase node and edge still matches: preflight → begin_pass → context → graph(T1) → recon/architecture/threat-model → prefilter → investigate → dedupe → critic/judge/validate → calibrate → patch/validate-fix → verify → gate → redteam → report → postflight. If any node name or ordering drifted, correct the diagram; if it matches, make no change. Record in the commit body that the diagrams were checked (state "verified against CLAUDE.md §3", not "looks right").

- [ ] **Step 4: Verify the worked SQLi example against the code**

The worked-example table (`skills/sec-overlay/README.md` lines 117–149) names concrete receipts and modules (`semgrep:<rule>`, `codeql:dataflow`, gate ladder Gate −1…Gate 3, `dedupe` fingerprint `sha256(sqli|injection|get_user)`, `calibrate` risk_score). Cross-check the receipt names against `helpers/README.md`'s `evidence.py` row (`_MECHANICAL` set) and the gate-ladder description in `CLAUDE.md` §4b. Confirm the module/artifact names in the "Artifact touched" column exist. Fix any name that no longer matches; otherwise no change. Note the check in the commit body.

- [ ] **Step 5: Verify no stale counts or identifiers remain**

Run:
```bash
cd plugins/sec-overlay/skills/sec-overlay
rg -n '~470|~75 |3 env-only|Three failures|sec[_-]harness' README.md helpers/README.md
```
Expected: no matches.

- [ ] **Step 6: Update governance docs and commit**

Add a `CHANGELOG.md` entry under `### Fixed`:
```
- Correct the sec-overlay README and helpers/README test counts to 575 tests / 2 env-only failures and verify the diagrams and worked example against the current pipeline.
```
Commit:
```bash
git add plugins/sec-overlay/skills/sec-overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        README.md CHANGELOG.md
git commit -m "docs(sec-overlay): fix overview counts, verify diagrams"
```

---

## Task 5: Add six per-folder READMEs

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/agents/classes/README.md`
- Create: `plugins/sec-overlay/skills/sec-overlay/references/asvs/README.md`
- Create: `plugins/sec-overlay/skills/sec-overlay/references/codeguard/README.md`
- Create: `plugins/sec-overlay/skills/sec-overlay/references/hunting/README.md`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md`
- Modify (governance): `README.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the six folder READMEs the Task-6 hook will thereafter require on any change inside those folders.

**Common contract for every folder README (read once):**
- Start with an H1 naming the folder and one sentence on its job.
- One line per file: `` `filename` `` → what it is (form) and what consumes/produces it (function). Read each file's first 20–40 lines to describe it truthfully — do not guess from the name.
- End with the folder-README freshness rule: *"When a file here changes, update this README in the same commit (enforced by the pre-commit hook)."*
- Keep each file's line ≤100 chars where practical; match the terse, table-driven style of the existing `helpers/README.md`.

- [ ] **Step 1: Write `references/asvs/README.md` (the fully-worked pattern example)**

This folder has one file. Read `references/asvs/asvs_5.0.0.json` (structure only) and write:
```markdown
# `references/asvs/` — OWASP ASVS seed data

Curated ASVS 5.0 requirement seed consumed by the deterministic citation layer.

| File | Form & function |
|------|-----------------|
| `asvs_5.0.0.json` | A curated 12-item subset of OWASP ASVS 5.0.0 requirements (id, section, requirement text). Loaded by `helpers/sec_overlay/asvs.py` and attached to findings by `citations.py` / `rule_matcher.py` as advisory ASVS ids — never as tool receipts. |

When a file here changes, update this README in the same commit (enforced by the pre-commit hook).
```

- [ ] **Step 2: Write `references/codeguard/README.md`**

Seven files, all short checklists. Read each (they are ~400–530 B) and write an H1 + intro (one sentence: "Terse secure-coding checklists, one per domain, consumed by `codeguard.py` and the patch/triage agents for correct remediation shape.") followed by a 7-row table, one row per file (`codeguard-0-api-web-services.md`, `codeguard-0-authorization-access-control.md`, `codeguard-0-client-side-web-security.md`, `codeguard-0-cryptography.md`, `codeguard-0-file-handling-and-uploads.md`, `codeguard-0-input-validation-injection.md`, `codeguard-0-safe-c-functions.md`), each describing the domain the checklist covers. Close with the freshness rule.

- [ ] **Step 3: Write `references/hunting/README.md`**

Eight files. `CLAUDE.md` §6 already summarizes most; use it as the source of truth and expand per-file by reading each. H1 + intro (one sentence: "Deep exploit-reasoning companions loaded conditionally by attack surface; `methodology.md` and `anti-patterns.md` load always."). One row per file: `ai-agent.md` (LangChain/MCP/RAG), `anti-patterns.md` (per-class FP-trap callouts, always loaded), `business-logic.md`, `client-side.md` (SPA/browser), `graphql-injection.md`, `memory-native.md` (C/C++/Rust-unsafe/cgo only), `methodology.md` (always loaded, operational core of signal-over-noise), `web-protocol-auth.md` (proxies/JWT/OAuth/SAML). Close with the freshness rule.

- [ ] **Step 4: Write `agents/classes/README.md`**

Eleven files — per-attack-class prompt extensions injected into the investigate agent. Read the top of each and write an H1 + one sentence ("Attack-class prompt extensions; `investigate.md` loads the `classes/<key>.md` matching each candidate's class. `test_wiring.py` guards the wiring."), then an 11-row table describing each: `authn.md`, `authz.md`, `business-logic.md`, `config.md`, `context-bleed.md`, `crypto.md`, `excessive-agency.md`, `injection.md`, `prompt-injection.md`, `resource.md`, `ssrf.md`. Close with the freshness rule.

- [ ] **Step 5: Write `helpers/sec_overlay/README.md`**

71 modules. The parent `helpers/README.md` already carries the authoritative grouped module map. Do **not** duplicate all 71 rows here — instead write a short orientation that points at the parent map and covers only what the parent does not:
```markdown
# `sec_overlay/` — the Python core package

The deterministic pipeline package: SAST orchestration, the tool-receipt gate, finding identity,
scoring, reporting, campaign state, and per-repo memory. Stdlib-only (no runtime dependencies).

**The authoritative, grouped module map lives in [`../README.md`](../README.md#sec_overlay--module-map-grouped-by-job)** — that
table lists every module by job and is kept current with the code. This file is the in-package
entry point; read the parent map for the full inventory.

- Package layout: ~71 modules at the top level, plus the `correlate/` subpackage (cross-repo
  correlation — see the parent map's `sec_overlay/correlate/` section).
- Two in-code invariants enforced here: the tool-receipt gate (`evidence.py` + `findings_gate.py`)
  and never-silent backends (`prefilter.py`). See [`../README.md`](../README.md#the-two-invariants-in-code).
- CLI-callable modules (`python -m sec_overlay.<module>`) are listed in the parent map.

When a module here changes, update the module map in [`../README.md`](../README.md) **and** this
pointer if the package layout changed — in the same commit (enforced by the pre-commit hook).
```
Verify the two anchor links resolve (GitHub slugifies `## sec_overlay/ — module map, grouped by job` to `#sec_overlay--module-map-grouped-by-job` and `## The two invariants, in code` to `#the-two-invariants-in-code`). If the parent headings differ, correct the anchors to match.

- [ ] **Step 6: Write `helpers/tests/README.md`**

78 test files — too many for one-line-each without noise. Group by what they guard, and call out the structural guards by name. Write:
```markdown
# `tests/` — the deterministic test suite

78 pytest files, 575 tests. Run from `helpers/`: `uv run pytest -q`. Two failures on a clean
checkout are environmental (gitignored bench corpus, excluded semgrep submodule) — see the skill
[`CLAUDE.md`](../../CLAUDE.md) §2.

## Structural guards (know these)

| Test | Guards |
|------|--------|
| `test_contracts.py` | Prompt↔schema drift: a `Finding` JSON example in an agent prompt must parse against the real `models.py`. |
| `test_finding_schema.py` | The `Finding` record stays consistent with `references/finding.schema.json`. |
| `test_wiring.py` | Silent-backend / clsmap / dead-link regressions and attack-class routing. |
| `test_docs_invariants.py` | Documentation contracts: prompt-constants block presence, `finding-template.md` sections, agent-prompt rules. |

## The rest

The remaining files are per-module unit tests named `test_<module>.py` mirroring
`sec_overlay/<module>.py` (e.g. `test_calibrate.py`, `test_verify.py`, `test_dedupe.py`), plus
bench/citation tests (`test_bench.py`, `test_citations.py`) that need local seed data.

When you add or change a test file, update this README's counts and guard list in the same commit
(enforced by the pre-commit hook).
```
Before committing, confirm the "78 files, 575 tests" figures still match `ls tests/*.py | wc -l` and `uv run pytest -q --collect-only | tail -1`.

- [ ] **Step 7: Validate all six new READMEs render and links resolve**

Run:
```bash
cd plugins/sec-overlay/skills/sec-overlay
for f in agents/classes references/asvs references/codeguard references/hunting helpers/sec_overlay helpers/tests; do
  test -f "$f/README.md" && echo "ok $f" || echo "MISSING $f"
done
rg -n -i 'sec[_-]harness|SEC_HARNESS|go port' agents/classes/README.md references/asvs/README.md \
  references/codeguard/README.md references/hunting/README.md helpers/sec_overlay/README.md helpers/tests/README.md
```
Expected: six `ok` lines, no stale-identifier matches.

- [ ] **Step 8: Update governance docs and commit**

Add a `CHANGELOG.md` entry under `### Added`:
```
- Add per-folder READMEs for agents/classes, references/asvs, references/codeguard, references/hunting, helpers/sec_overlay, and helpers/tests.
```
Add a root `README.md` Status line: "Added six per-folder READMEs under the sec-overlay skill." Commit:
```bash
git add plugins/sec-overlay/skills/sec-overlay/agents/classes/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/asvs/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/codeguard/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/hunting/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        README.md CHANGELOG.md
git commit -m "docs(sec-overlay): add six per-folder READMEs"
```
Note: this commit does **not** touch other files inside those six folders, so the new READMEs satisfy the (Task-6, not-yet-installed) folder rule trivially; the existing `plugins/` guide-dir rule is satisfied because the changes are under `plugins/` and this commit is docs — but the current hook's `plugins/` rule requires `plugins/README.md`. **There is no `plugins/README.md`.** Confirm before committing: run `git ls-files plugins/README.md`. If absent, the existing hook's `guide_dirs` loop checks `plugins/README.md` only when files *directly* match `^plugins/` and not `plugins/README.md`; since these are deep paths it still triggers. If the commit is blocked for a missing `plugins/README.md`, stop and surface it — creating `plugins/README.md` is out of this task's scope and needs a decision. (See Task 6 Step 1's note; the generalized rule replaces this brittle top-level check.)

- [ ] **Step 9: Resolve the `plugins/README.md` gate if it blocks**

If Step 8 was blocked: the cleanest fix is to land Task 6 first (it generalizes the hook to per-folder READMEs and can drop the brittle `plugins`/`scripts` top-level special-case, or keep it while also creating a minimal `plugins/README.md`). Re-order execution so Task 6 precedes Task 5 if the gate blocks, or add `plugins/README.md` under a separate decision. Record which path was taken in the commit body.

---

## Task 6: Extend the pre-commit hook for per-folder README freshness

**Files:**
- Modify: `scripts/hooks/pre-commit-check.sh`
- Create: `scripts/hooks/test-pre-commit-check.sh`
- Modify: `scripts/README.md` (folder README — this folder's files change)
- Modify (governance): `README.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the generalized folder-README enforcement referenced by root README Governance and skill `CLAUDE.md` §8.

**Invariant this hook must satisfy:** for every staged non-README file whose immediate directory contains a tracked `README.md`, that `README.md` must also be staged; otherwise the commit is rejected naming the folder. A folder whose README is being newly added in the same commit passes (the README is staged). A folder with no tracked README is not gated.

- [ ] **Step 1: Write the failing Bash test first (red)**

Create `scripts/hooks/test-pre-commit-check.sh`:
```bash
#!/usr/bin/env bash
# Invocation tests for pre-commit-check.sh. Builds throwaway git repos and asserts exit codes.
set -euo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/pre-commit-check.sh"
pass=0
fail=0

# Run the hook inside a fresh temp repo seeded by $1 (a function), assert exit code $2.
run_case() {
  local name="$1" setup="$2" want="$3"
  local dir
  dir="$(mktemp -d)"
  (
    cd "$dir"
    git init -q
    git config user.email t@t.t
    git config user.name t
    git checkout -q -b work
    # Copy the hook under test into the temp repo so its relative logic runs there.
    mkdir -p scripts/hooks
    cp "$HOOK" scripts/hooks/pre-commit-check.sh
    "$setup"
    set +e
    bash scripts/hooks/pre-commit-check.sh >/dev/null 2>&1
    local got=$?
    set -e
    exit "$got"
  )
  local got=$?
  if [ "$got" -eq "$want" ]; then
    echo "ok   $name (exit $got)"; pass=$((pass + 1))
  else
    echo "FAIL $name (want $want, got $got)"; fail=$((fail + 1))
  fi
}

# Case A: change a file in a folder with a tracked README, README NOT staged -> block (exit 1).
setup_block() {
  mkdir -p pkg
  printf '# pkg\n' >pkg/README.md
  printf 'x\n' >pkg/thing.txt
  git add pkg/README.md pkg/thing.txt README.md CHANGELOG.md 2>/dev/null || true
  printf '# r\n' >README.md; printf '# c\n' >CHANGELOG.md
  git add README.md CHANGELOG.md pkg/README.md pkg/thing.txt
  git commit -q -m "seed"
  # Now stage a change to pkg/thing.txt WITHOUT restaging pkg/README.md.
  printf 'y\n' >>pkg/thing.txt
  printf 'changed\n' >>README.md
  printf 'changed\n' >>CHANGELOG.md
  git add pkg/thing.txt README.md CHANGELOG.md
}

# Case B: same change but README IS staged -> pass (exit 0).
setup_pass() {
  mkdir -p pkg
  printf '# pkg\n' >pkg/README.md
  printf 'x\n' >pkg/thing.txt
  printf '# r\n' >README.md; printf '# c\n' >CHANGELOG.md
  git add README.md CHANGELOG.md pkg/README.md pkg/thing.txt
  git commit -q -m "seed"
  printf 'y\n' >>pkg/thing.txt
  printf 'note\n' >>pkg/README.md
  printf 'changed\n' >>README.md
  printf 'changed\n' >>CHANGELOG.md
  git add pkg/thing.txt pkg/README.md README.md CHANGELOG.md
}

# Case C: folder has NO tracked README -> not gated -> pass (exit 0).
setup_no_readme() {
  mkdir -p pkg
  printf 'x\n' >pkg/thing.txt
  printf '# r\n' >README.md; printf '# c\n' >CHANGELOG.md
  git add README.md CHANGELOG.md pkg/thing.txt
  git commit -q -m "seed"
  printf 'y\n' >>pkg/thing.txt
  printf 'changed\n' >>README.md
  printf 'changed\n' >>CHANGELOG.md
  git add pkg/thing.txt README.md CHANGELOG.md
}

run_case "blocks when folder README not restaged" setup_block 1
run_case "passes when folder README restaged"    setup_pass 0
run_case "passes when folder has no README"      setup_no_readme 0

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
```

- [ ] **Step 2: Run the test to verify Case A fails (red)**

Run:
```bash
shellcheck scripts/hooks/test-pre-commit-check.sh
bash scripts/hooks/test-pre-commit-check.sh
```
Expected: `FAIL blocks when folder README not restaged (want 1, got 0)` — the current hook does not enforce the per-folder rule, so Case A wrongly passes. Cases B and C already pass. Overall exit non-zero. (If shellcheck flags style issues, fix them before proceeding.)

- [ ] **Step 3: Add the generalized per-folder rule to the hook (green)**

In `scripts/hooks/pre-commit-check.sh`, after the existing `guide_dirs` loop (line 41), append:
```bash
# General rule: any staged file whose immediate folder has a tracked README.md
# requires that README.md to be staged too.
while IFS= read -r f; do
  [ -z "$f" ] && continue
  d=$(dirname "$f")
  [ "$d" = "." ] && continue
  readme="$d/README.md"
  [ "$f" = "$readme" ] && continue
  if git ls-files --error-unmatch "$readme" >/dev/null 2>&1; then
    if ! grep -qx "$readme" <<<"$staged"; then
      echo "error: this commit changes ${f} but does not update ${readme}." >&2
      echo "fix: update ${readme} in the same commit and stage it." >&2
      exit 1
    fi
  fi
done <<<"$staged"
```
Note: `git ls-files --error-unmatch` treats the index as source of truth, so a README added in the same commit (already staged) counts as tracked and passes the grep. Keep or drop the older `guide_dirs` special-case per the Task-5 Step-9 decision; if kept, it is redundant but harmless. If dropped, state so in the commit body.

- [ ] **Step 4: Run the test to verify all cases pass (green)**

Run:
```bash
shellcheck scripts/hooks/pre-commit-check.sh scripts/hooks/test-pre-commit-check.sh
shfmt -d scripts/hooks/pre-commit-check.sh scripts/hooks/test-pre-commit-check.sh
bash scripts/hooks/test-pre-commit-check.sh
```
Expected: `pass=3 fail=0` and exit 0; shellcheck clean; `shfmt -d` shows no diff (run `shfmt -w` if it does).

- [ ] **Step 5: Document the rule in prose (skill CLAUDE.md and root README)**

`CLAUDE.md` §8 was already rewritten in Task 3 to describe the folder-README hook — confirm its wording matches the now-installed rule (per-folder, not just `agents/helpers/references`). The root README Governance bullet from Task 2 already states the folder-README rule. Confirm both read correctly; adjust only if the installed behavior differs from the prose.

- [ ] **Step 6: Update `scripts/README.md`**

`scripts/` is a Directory-Guide folder with its own README. Read it, then add a row/paragraph documenting the new test file `test-pre-commit-check.sh` (invocation test for the pre-commit hook; run with `bash scripts/hooks/test-pre-commit-check.sh`) and note the generalized per-folder README rule the hook now enforces.

- [ ] **Step 7: Update governance docs and commit**

Add a `CHANGELOG.md` entry under `### Changed`:
```
- Extend the pre-commit hook to require a folder's README.md whenever files in that folder change, with a Bash invocation test.
```
Add a root `README.md` Status line: "Generalized the pre-commit hook to enforce per-folder README freshness (with a Bash test)." Commit:
```bash
git add scripts/hooks/pre-commit-check.sh scripts/hooks/test-pre-commit-check.sh \
        scripts/README.md README.md CHANGELOG.md
git commit -m "feat(hooks): enforce per-folder README freshness"
```
Expected: the hook now runs against its own commit — since only `scripts/` files changed and `scripts/README.md` is staged, and README + CHANGELOG are staged, it passes.

---

## Self-Review

**Spec coverage:**
- Spec §1 (remove Go from 4 live docs + contract-note replacement) → Task 1. ✓
- Spec §2 (root README template) → Task 2. ✓
- Spec §3 (skill CLAUDE.md refocus, surgical per user) → Task 3. ✓
- Spec §4 (skill overview README) → Task 4 (edit-and-verify per Deviation 2). ✓
- Spec §5 (six per-folder READMEs) → Task 5. ✓
- Spec §6 (hook + test + governance-doc note) → Task 6 (Bash test per Deviation 3). ✓
- Spec commit grouping (6 commits) → Tasks 1–6, one commit each. ✓

**Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". Content for edits is verbatim; the six folder READMEs give an exact file inventory, a fully-worked example (asvs), authored templates (sec_overlay, tests), and a per-file contract with the authoritative source to derive the rest — appropriate for docs derived from reading files.

**Type/name consistency:** Counts are uniform everywhere — **575 tests, 573 pass, 2 env-only failures, 78 test files**. The two failing node ids are identical across Tasks 1/3/4/5/6. The contract-note phrasing (`test_contracts.py` + `test_finding_schema.py` + `finding.schema.json`) is identical in Tasks 1, 4, and 6. Branch name `docs/sec-overlay-doc-overhaul` matches the current branch.

**Known ordering risk:** Task 5 Step 8/9 flags the existing hook's `plugins/README.md` special-case. If it blocks, execute Task 6 before Task 5 (Task 6 generalizes the rule). The executor must decide at that point; the plan surfaces it rather than hiding it.
