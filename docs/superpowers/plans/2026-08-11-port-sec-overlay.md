# Port sec-harness → sec-overlay Plugin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the `sec-harness` skill from `github.com/cjbischoff/security-harness` into this marketplace as the `sec-overlay` plugin, renaming the identifier throughout, and prove it passes its own test suite and `claude plugin validate`.

**Architecture:** Copy the full source skill tree into `plugins/sec-overlay/skills/sec-overlay/`, replacing the placeholder. Apply four case-sensitive token replacements across every ported file, rename the Python package directory, adapt the SKILL.md path anchors to `${CLAUDE_PLUGIN_ROOT}`, and drop the semgrep submodule (documented as a prerequisite). The ported pytest suite is the safety net for the rename.

**Tech Stack:** Python 3.13 (source requires ≥3.12), `uv` for env/test/lint, `ruff`, `ty`, `claude plugin validate`. Source tree is text-only (`.md`, `.py`, `.json`, `.yaml`, `.toml`, `.lock`, `.diff`).

## Global Constraints

- Work only on branch `feat/port-sec-overlay`. Never commit to `main`.
- Plugin `version` stays `0.1.0`. Do not bump.
- Rename is exactly four case-sensitive substring replacements, nothing else:
  `sec_harness`→`sec_overlay`, `sec-harness`→`sec-overlay`, `SEC_HARNESS_HOME`→`SEC_OVERLAY_HOME`, `HARNESS_ROOT`→`OVERLAY_ROOT`.
- Do NOT change the bare word `harness` in prose, nor `{{HELPERS_DIR}}`.
- Do NOT ship the `helpers/rules/semgrep` submodule.
- Never use `rm -rf`; use `trash`.
- Conventional Commits, summary <50 chars, body wrapped at 72.
- Governance hooks: every commit that changes tracked files must update root `README.md` and `CHANGELOG.md` in the same commit; a commit touching files under `plugins/` must also update `plugins/README.md`. Fold these into each task's commit step.
- Source clone lives at `${TMPDIR}/gh-clones-${CLAUDE_SESSION_ID}/security-harness` (shallow; submodule not fetched). Re-clone with `gh repo clone cjbischoff/security-harness <dest> -- --depth 1` if absent.

---

### Task 1: Replace the placeholder skill with the source tree

**Files:**
- Remove: `plugins/sec-overlay/skills/sec-overlay/SKILL.md`, `plugins/sec-overlay/skills/sec-overlay/scripts/run.py` (placeholder)
- Create: `plugins/sec-overlay/skills/sec-overlay/**` (full source tree, minus `.git` and the semgrep submodule)
- Modify: `README.md`, `CHANGELOG.md`, `plugins/README.md`

**Interfaces:**
- Produces: the unrenamed source tree in place, ready for the rename pass (Task 2). All later tasks operate on `plugins/sec-overlay/skills/sec-overlay/`.

- [ ] **Step 1: Confirm the clone exists**

```bash
CLONE="${TMPDIR:-/tmp}/gh-clones-${CLAUDE_SESSION_ID}/security-harness"
test -d "$CLONE/skills/sec-harness" || gh repo clone cjbischoff/security-harness "$CLONE" -- --depth 1
ls "$CLONE/skills/sec-harness/SKILL.md"
```
Expected: the SKILL.md path prints (no error).

- [ ] **Step 2: Remove the placeholder skill directory**

```bash
trash plugins/sec-overlay/skills/sec-overlay
```
Keep `plugins/sec-overlay/.claude-plugin/plugin.json` (edited later, not removed).

- [ ] **Step 3: Copy the source tree, excluding .git and the submodule**

```bash
CLONE="${TMPDIR:-/tmp}/gh-clones-${CLAUDE_SESSION_ID}/security-harness"
DST="plugins/sec-overlay/skills/sec-overlay"
mkdir -p "$DST"
rsync -a --exclude='.git' --exclude='helpers/rules/semgrep' \
  "$CLONE/skills/sec-harness/" "$DST/"
```

- [ ] **Step 4: Verify the copy landed and the submodule did not**

```bash
find plugins/sec-overlay/skills/sec-overlay -type f | wc -l   # expect ~271
test ! -e plugins/sec-overlay/skills/sec-overlay/helpers/rules/semgrep
ls plugins/sec-overlay/skills/sec-overlay/helpers/rules/smoke.yaml   # must exist
ls plugins/sec-overlay/skills/sec-overlay/helpers/sec_harness/cli.py # unrenamed yet
```
Expected: count near 271, `smoke.yaml` and unrenamed `sec_harness/cli.py` present, semgrep dir absent.

- [ ] **Step 5: Update governance docs**

In `README.md` artifact inventory: replace the two placeholder rows (`.../SKILL.md` "logic lives in scripts/" and `.../scripts/run.py`) with rows for the ported skill (`plugins/sec-overlay/skills/sec-overlay/SKILL.md` — agentic security-audit harness playbook; `plugins/sec-overlay/skills/sec-overlay/helpers/` — Python core). Update the "Status" and "Next steps" sections to reflect the port instead of the placeholder.
In `plugins/README.md`: update the `sec-overlay/` row to "Agentic security-audit harness; SAST + multi-agent investigation. Python core under `skills/sec-overlay/helpers/`."
In `CHANGELOG.md` under `## 0.1.0` → `### Added`: add "Port the sec-harness skill source into the sec-overlay plugin."

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(sec-overlay): import sec-harness source tree"
```
Expected: hooks pass (README + CHANGELOG updated).

---

### Task 2: Apply the rename

**Files:**
- Rename dir: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_harness/` → `.../helpers/sec_overlay/`
- Modify: every text file under `plugins/sec-overlay/skills/sec-overlay/` containing a target token
- Modify: `README.md`, `CHANGELOG.md`, `plugins/README.md`

**Interfaces:**
- Consumes: the unrenamed tree from Task 1.
- Produces: the package importable as `sec_overlay`; env var `SEC_OVERLAY_HOME`; token `{{OVERLAY_ROOT}}`; sidecar dir `.sec-overlay`. Later tasks import `sec_overlay.cli`, `sec_overlay.state`, etc.

- [ ] **Step 1: Rename the package directory**

```bash
SK=plugins/sec-overlay/skills/sec-overlay
mv "$SK/helpers/sec_harness" "$SK/helpers/sec_overlay"
```

- [ ] **Step 2: Apply the four case-sensitive replacements to all text files**

```bash
SK=plugins/sec-overlay/skills/sec-overlay
grep -rlZ -e 'sec_harness' -e 'sec-harness' -e 'SEC_HARNESS_HOME' -e 'HARNESS_ROOT' "$SK" \
  | xargs -0 sed -i '' \
      -e 's/sec_harness/sec_overlay/g' \
      -e 's/sec-harness/sec-overlay/g' \
      -e 's/SEC_HARNESS_HOME/SEC_OVERLAY_HOME/g' \
      -e 's/HARNESS_ROOT/OVERLAY_ROOT/g'
```
(macOS `sed` requires the empty-string `-i ''`.)

- [ ] **Step 3: Verify no target token survives**

```bash
SK=plugins/sec-overlay/skills/sec-overlay
grep -rn -e 'sec_harness' -e 'sec-harness' -e 'SEC_HARNESS_HOME' -e 'HARNESS_ROOT' "$SK"
```
Expected: no output (exit 1 from grep). If anything prints, it is a missed rename — fix it.

- [ ] **Step 4: Verify the package directory and key modules renamed**

```bash
SK=plugins/sec-overlay/skills/sec-overlay
ls "$SK/helpers/sec_overlay/cli.py" "$SK/helpers/sec_overlay/state.py"
grep -n 'name = "sec-overlay"' "$SK/helpers/pyproject.toml"
grep -n 'packages = \["sec_overlay"\]' "$SK/helpers/pyproject.toml"
grep -rn 'os.environ.get("SEC_OVERLAY_HOME")' "$SK/helpers/sec_overlay/repo_memory.py"
```
Expected: all four print a match.

- [ ] **Step 5: Residual case-check (informational)**

```bash
grep -rniE 'sec[-_]harness' plugins/sec-overlay/skills/sec-overlay || echo "clean"
```
Expected: `clean`. (Catches any Titlecase variant the case-sensitive pass missed.)

- [ ] **Step 6: Update governance docs and commit**

`CHANGELOG.md` `### Added`: add "Rename the ported identifier from sec-harness/sec_harness to sec-overlay/sec_overlay (including SEC_OVERLAY_HOME and the {{OVERLAY_ROOT}} token)." Touch `README.md` (bump the Status line to note the rename is applied) and `plugins/README.md` (no content change needed beyond Task 1; re-save to satisfy the folder-README hook only if the hook flags it).

```bash
git add -A
git commit -m "feat(sec-overlay): rename identifier to sec-overlay"
```

---

### Task 3: Verify packaging and imports

**Files:**
- Read: `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml`, `uv.lock`
- Modify (only if a fix is needed): `pyproject.toml`, `README.md`, `CHANGELOG.md`, `plugins/README.md`

**Interfaces:**
- Consumes: renamed package from Task 2.
- Produces: a resolvable dev environment so Task 5 can run the suite.

- [ ] **Step 1: Sync the dev environment**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv sync
```
Expected: environment resolves (dev group: pytest, ruff, ty). If `uv.lock` is stale after the pyproject `name` change, run `uv lock` and include the updated `uv.lock` in the Task 5 commit.

- [ ] **Step 2: Import the renamed package**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -c "import sec_overlay, sec_overlay.cli, sec_overlay.state, sec_overlay.correlate; print('import ok')"
```
Expected: `import ok`. An `ImportError` naming `sec_harness` means a missed rename in an import — return to Task 2 Step 2 scope.

- [ ] **Step 3: Verify the CLI entry runs**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -m sec_overlay.cli --help
```
Expected: usage text prints (exit 0).

- [ ] **Step 4: Commit only if a fix was made**

If `uv lock` changed `uv.lock` or a `pyproject.toml` fix was needed:
```bash
git add -A
git commit -m "fix(sec-overlay): relock deps after package rename"
```
(Update `README.md`/`CHANGELOG.md`/`plugins/README.md` in that commit.) If nothing changed, skip.

---

### Task 4: Adapt SKILL.md path anchors and document the semgrep prerequisite

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/SKILL.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/README.md`
- Modify: `README.md`, `CHANGELOG.md`, `plugins/README.md`

**Interfaces:**
- Consumes: renamed SKILL.md (from Task 2) whose anchor text now reads `{{OVERLAY_ROOT}}` = absolute path to `skills/sec-overlay/` and `{{HELPERS_DIR}}` = absolute path to `skills/sec-overlay/helpers`.
- Produces: run instructions valid inside the installed plugin cache.

- [ ] **Step 1: Point the "Deterministic scan" block at the plugin root**

In SKILL.md, the block currently reads:
```
From the harness helpers directory:

    cd skills/sec-overlay/helpers
    uv run python -m sec_overlay.cli scan \
```
Change the intro line and `cd` to:
```
From the harness helpers directory (inside the installed plugin, this is
`${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/helpers`):

    cd "${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/helpers"
    uv run python -m sec_overlay.cli scan \
```

- [ ] **Step 2: Define the anchors from `${CLAUDE_PLUGIN_ROOT}` in the "Running a full audit" preamble**

Find the sentence defining `{{OVERLAY_ROOT}}` (absolute path to `skills/sec-overlay/`) and `{{HELPERS_DIR}}` (absolute path to `skills/sec-overlay/helpers`). Immediately after it, add one sentence:
```
When this skill runs as the installed `sec-overlay` plugin, set
`{{OVERLAY_ROOT}}` = `${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay` and
`{{HELPERS_DIR}}` = `${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/helpers`.
```

- [ ] **Step 3: Document the semgrep ruleset as a prerequisite**

In SKILL.md near the first `--config rules/smoke.yaml` usage, add one sentence:
```
The bundled `rules/smoke.yaml` is a minimal ruleset. For fuller semgrep
coverage, point `--config` (and the recon agent's `rulesets`) at your own
semgrep ruleset; the semgrep-rules submodule is not shipped with this plugin.
```
In the skill's `README.md`, replace any "Clone with `--recurse-submodules`" / semgrep-submodule setup guidance with the same prerequisite note (the submodule is not part of the plugin).

- [ ] **Step 4: Verify the edits**

```bash
SK=plugins/sec-overlay/skills/sec-overlay
grep -n 'CLAUDE_PLUGIN_ROOT' "$SK/SKILL.md"        # ≥2 hits (scan block + anchors)
grep -n 'not shipped\|not part of the plugin' "$SK/SKILL.md" "$SK/README.md"
```
Expected: the plugin-root references and the prerequisite note are present.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs(sec-overlay): fix plugin paths and semgrep note"
```
(Update root `README.md`/`CHANGELOG.md`/`plugins/README.md` in this commit.)

---

### Task 5: Run the test suite and linters to green

**Files:**
- Read/modify as needed: any file under `plugins/sec-overlay/skills/sec-overlay/helpers/`
- Modify: `README.md`, `CHANGELOG.md`, `plugins/README.md`

**Interfaces:**
- Consumes: renamed, importable package.
- Produces: a green suite proving the rename preserved behavior.

- [ ] **Step 1: Run the suite**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
```
Expected: all tests pass. Known-tolerable environment failures documented in the source (bench corpus is gitignored; semgrep-rules submodule absent) may appear — confirm each failing test is one of those categories and is NOT caused by the rename. A failure mentioning `sec_harness`, `SEC_HARNESS_HOME`, `.sec-harness`, or `OVERLAY_ROOT`/`HARNESS_ROOT` is a rename bug — fix the offending file, not the test.

- [ ] **Step 2: Triage any failures**

For each failure: read the assertion. If it is the semgrep-submodule-absent or gitignored-bench-corpus category, record it in the commit message as a known env-only skip. Otherwise fix the root cause (a missed rename or a doc-invariant referencing a renamed path) and re-run Step 1 until only known env-only failures remain.

- [ ] **Step 3: Run ruff and ty**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run ruff check .
uv run ty check
```
Expected: clean. Fix any warning introduced by the rename (the source was clean, so any new finding traces to the port). Do not add ignores without a justification comment.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test(sec-overlay): pass suite after rename"
```
Body: list any known env-only failures and why they are expected. Update root `README.md`/`CHANGELOG.md`/`plugins/README.md`.

---

### Task 6: Update the manifest, validate the plugin, finalize docs

**Files:**
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`, `CHANGELOG.md`, `plugins/README.md`

**Interfaces:**
- Consumes: green, renamed plugin.
- Produces: a marketplace that validates and describes the real skill.

- [ ] **Step 1: Update the plugin manifest description**

In `plugins/sec-overlay/.claude-plugin/plugin.json`, keep `name` `sec-overlay` and `version` `0.1.0`; set `description` to: `Agentic security-audit harness: runs SAST, investigates candidates with multi-agent gates, and emits SARIF + Markdown reports.`

- [ ] **Step 2: Update the marketplace manifest description**

In `.claude-plugin/marketplace.json`, set the `sec-overlay` entry `description` to match the plugin manifest description from Step 1.

- [ ] **Step 3: Validate the plugin**

```bash
claude plugin validate plugins/sec-overlay
```
Expected: validation passes. Fix any reported manifest/structure error before continuing.

- [ ] **Step 4: Validate the marketplace**

```bash
claude plugin validate .
```
Expected: passes (workspace desired outcome).

- [ ] **Step 5: Final governance-doc pass**

Ensure `README.md` "Status", "Next steps", and artifact inventory reflect the finished port (no placeholder references remain). Ensure `plugins/README.md` describes the real skill. Add a final `CHANGELOG.md` entry: "Update sec-overlay manifest descriptions to the agentic security-audit harness."

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(sec-overlay): finalize manifests and validate"
```

---

### Task 7: Merge gate (requires user approval)

- [ ] **Step 1: Summarize the result** — file count ported, rename verification output, pytest/ruff/ty status, `claude plugin validate` status, and any known env-only test skips.
- [ ] **Step 2: Ask the user** whether to merge `feat/port-sec-overlay` into `main`. Do NOT merge without explicit approval (workspace rule).
- [ ] **Step 3 (on approval):** `git checkout main && git merge --no-ff feat/port-sec-overlay && git branch -d feat/port-sec-overlay`.

---

## Self-Review

**Spec coverage:**
- Full rename incl. Python namespace → Task 2 (four replacements + dir rename), verified Task 3, proven Task 5. ✓
- Port everything (272 files) → Task 1 (rsync full tree). ✓
- semgrep documented as prerequisite, submodule dropped → Task 1 Step 3 exclude, Task 4 Step 3 docs. ✓
- Token renames `HARNESS_ROOT`→`OVERLAY_ROOT`, `SEC_HARNESS_HOME`→`SEC_OVERLAY_HOME` → Task 2 Global Constraints + Step 2. ✓
- Plugin-path adaptation → Task 4. ✓
- Verification gates (pytest, ruff, ty, plugin validate) → Tasks 5–6. ✓
- Governance (branch, README/CHANGELOG/plugins-README per commit, no version bump, user-approved merge) → Global Constraints + Task 7. ✓

**Placeholder scan:** No TBD/TODO; every step has concrete commands. Triage steps (Task 5 Step 2) describe the exact decision rule, not "handle errors." ✓

**Type/name consistency:** `sec_overlay` package, `sec_overlay.cli`/`.state`/`.correlate` modules, `SEC_OVERLAY_HOME`, `{{OVERLAY_ROOT}}`, `.sec-overlay` sidecar used consistently across Tasks 2–6. ✓
