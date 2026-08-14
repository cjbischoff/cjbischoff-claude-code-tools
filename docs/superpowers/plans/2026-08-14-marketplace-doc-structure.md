# Marketplace Documentation Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split marketplace-level and plugin-level documentation: root CLAUDE.md governs governance and scaffolding, sec-overlay carries its own CLAUDE.md/README/CHANGELOG, a plugin template exists, and the prek hook routes changelog requirements.

**Architecture:** Four commits on branch `docs/claude-md-marketplace-20260814`. Commits 1–3 are documentation moves and additions that run under the current hook rules; commit 4 changes the hook and ships its test.

**Tech Stack:** Markdown, bash (prek hook + test), `claude plugin validate`.

**Spec:** `docs/superpowers/specs/2026-08-14-marketplace-doc-structure-design.md`

## Global Constraints

- Branch: `docs/claude-md-marketplace-20260814`; never commit to main; never `git add -A`; never `--no-verify`.
- Conventional Commits, subject under 50 chars.
- Until Task 4 lands, every commit stages root `README.md` + `CHANGELOG.md`, and the folder `README.md` of any folder whose tracked files change.
- Common Changelog section order: Changed, Added, Removed, Fixed.
- Every CLAUDE.md targets under 200 lines.
- No governance rule stated in more than one file; plugin docs link to root governance.
- Skill CLAUDE.md is a shipping file: Task 1 bumps `plugins/sec-overlay/.claude-plugin/plugin.json` 0.2.0 → 0.2.1.

---

### Task 1: sec-overlay documentation split

**Files:**
- Create: `plugins/sec-overlay/README.md`, `plugins/sec-overlay/CHANGELOG.md`, `plugins/sec-overlay/CLAUDE.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md`, `plugins/sec-overlay/skills/sec-overlay/README.md`, `plugins/sec-overlay/.claude-plugin/plugin.json`, `plugins/README.md`, `README.md`, `CHANGELOG.md`

**Interfaces:**
- Produces: `plugins/sec-overlay/CHANGELOG.md` (Task 4's hook requires it staged on plugin commits); the plugin-root doc trio Task 3's template mirrors.

- [ ] **Step 1: Create `plugins/sec-overlay/README.md`** — user-facing. Content: one-paragraph description (reuse the first two paragraphs of the skill README), install block (`/plugin marketplace add cjbischoff/cjbischoff-claude-code-tools`, `/plugin install sec-overlay@cjbischoff-claude-code-tools`), prerequisites (semgrep, codeql + language packs, ast-grep, osv-scanner, `uv`; semgrep ruleset is user-supplied), quick start (the smoke-scan block from the skill README "How to run it"), and a links table to `CHANGELOG.md`, `skills/sec-overlay/README.md` (deep dive), `skills/sec-overlay/SKILL.md` (playbook).

- [ ] **Step 2: Create `plugins/sec-overlay/CHANGELOG.md`** — Common Changelog header, then backfilled releases:

```markdown
## 0.2.0 - 2026-08-12
### Changed
- Default SARIF output to suppressed-full and populate driver.rules.
### Added
- Add systemic finding clustering, per-run self-score, and run-economics report section.
- Add external-boundary disposition: risk cap, ingested-package scope check, lead bucket.

## 0.1.0 - 2026-08-11
### Added
- Initial release: agentic security-audit harness (SAST prefilter, multi-agent gate ladder, SARIF + Markdown reports).
```

- [ ] **Step 3: Create `plugins/sec-overlay/CLAUDE.md`** — maintainer manual. Sections: (1) one-line governance pointer ("Governance — branching, commits, changelogs, version bumps — lives in the root `CLAUDE.md`; nothing here overrides it."); (2) "Developing the skill" — move old skill-CLAUDE.md §7 verbatim; (3) "Documentation — READMEs track code" — move old §8 verbatim; (4) "History" — move the 2026-07-31 `secrets.py` reconstruction paragraph from old §2. Note in the header that this file never loads for plugin installers (docs-verified).

- [ ] **Step 4: Trim `skills/sec-overlay/CLAUDE.md`** — delete old §1, §7, §8 and the `secrets.py` history paragraph; keep §0 mission, §2 env prerequisites, §3 how to run, §4 signal architecture, §5 artifacts, §6 references. Renumber to §0–§5. Update the header: the file is the operational companion `SKILL.md` points to; maintainer content lives in `plugins/sec-overlay/CLAUDE.md`.

- [ ] **Step 5: Repoint references.** Run `rg -n 'CLAUDE\.md' plugins/sec-overlay/skills/sec-overlay/{README.md,SKILL.md}` and fix every section reference (for example README's "`CLAUDE.md` §3" → new number; "Git protocol… CLAUDE.md" row → plugin-root CLAUDE.md; the version-bump/docs-track-code notes in the skill README "Develop" section → link `../../CLAUDE.md`).

- [ ] **Step 6: Bump version** — `plugins/sec-overlay/.claude-plugin/plugin.json` `"version": "0.2.1"`.

- [ ] **Step 7: Update governance docs** — `plugins/README.md` (describe the plugin-root doc trio convention), root `README.md` artifact inventory (add the three new files), root `CHANGELOG.md` Unreleased→Added entry.

- [ ] **Step 8: Verify** — `claude plugin validate .` passes; `wc -l` on both plugin CLAUDE.md files < 200; `rg -n '§[0-9]' plugins/sec-overlay/` shows no stale numbers.

- [ ] **Step 9: Commit**

```bash
git add plugins/sec-overlay/README.md plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/CLAUDE.md \
  plugins/sec-overlay/skills/sec-overlay/CLAUDE.md plugins/sec-overlay/skills/sec-overlay/README.md \
  plugins/sec-overlay/.claude-plugin/plugin.json plugins/README.md README.md CHANGELOG.md
git commit -m "docs(sec-overlay): split plugin docs by audience"
```

---

### Task 2: root CLAUDE.md rewrite

**Files:**
- Modify: `CLAUDE.md`, `README.md`, `CHANGELOG.md`

**Interfaces:**
- Produces: the changelog-routing rule text Task 4's hook implements; the "New plugin" checklist that points at Task 3's `docs/templates/plugin/`.

- [ ] **Step 1: Rewrite `CLAUDE.md`** with exactly these sections, under 200 lines:
  1. **Purpose + marketplace contract** — keep current Purpose/Desired outcome content.
  2. **Governance** — keep current branching/commit/CodeRabbit rules, replace the changelog rule with routing: "A commit whose changes are all inside `plugins/<name>/` updates that plugin's `CHANGELOG.md` (and its `plugin.json` version when shipping files change). A commit touching anything outside `plugins/` updates the root `CHANGELOG.md` and root `README.md`. Mixed commits do both." Keep the folder-README rule and the shipping-file/version-bump rule verbatim. Add: "Keep every CLAUDE.md under 200 lines."
  3. **New plugin** — checklist: copy `docs/templates/plugin/` to `plugins/<name>/`, replace `{{PLACEHOLDER}}` markers, register in `.claude-plugin/marketplace.json`, run `claude plugin validate .`, first entry in the plugin changelog at 0.1.0.
  4. **Release process** — bump `plugin.json` semver by commit type, add plugin changelog entry, branch → PR → wait for CodeRabbit walkthrough → merge on approval; users only receive updates on a version bump.
  5. **Routing rule** — "When improving an existing plugin, `plugins/<name>/CLAUDE.md` governs the specifics; plugin detail never lands in this file."
  6. **Decisions** — keep current list; add: per-plugin changelogs + plugin-root doc trio (supersedes single root changelog for plugin changes); plugin CLAUDE.md files never load for installers, so maintainer manuals are safe at the plugin root; CLAUDE.md 200-line target.
  7. **OpenWiki** — merge the two current OpenWiki sections into one, dropping duplicated lines.

- [ ] **Step 2: Update root `README.md`** — Contributing section mentions the doc split; Directory Guide unchanged; CHANGELOG scope note ("repo-level changes; plugin changes live in `plugins/<name>/CHANGELOG.md`").

- [ ] **Step 3: Root `CHANGELOG.md`** Unreleased→Changed entry for the rewrite.

- [ ] **Step 4: Verify** — `wc -l CLAUDE.md` < 200; `rg -c 'OpenWiki' CLAUDE.md` confirms a single section.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md CHANGELOG.md
git commit -m "docs: focus root CLAUDE.md on marketplace"
```

---

### Task 3: plugin template

**Files:**
- Create: `docs/templates/plugin/.claude-plugin/plugin.json`, `docs/templates/plugin/README.md`, `docs/templates/plugin/CLAUDE.md`, `docs/templates/plugin/CHANGELOG.md`, `docs/templates/plugin/skills/skill-name/SKILL.md`
- Modify: `docs/README.md`, `README.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes: the root CLAUDE.md "New plugin" checklist from Task 2 (template path must match `docs/templates/plugin/`).

- [ ] **Step 1: Create the five skeletons.** `plugin.json`:

```json
{
  "name": "{{plugin-name}}",
  "description": "{{one-line description}}",
  "version": "0.1.0",
  "author": { "name": "Christopher Bischoff" }
}
```

`README.md`: title, description placeholder, install block with `{{plugin-name}}`, Prerequisites and Quick start headings with `{{...}}` bodies, links table to `CHANGELOG.md` and `skills/{{skill-name}}/SKILL.md`. `CLAUDE.md`: governance pointer line (copy from sec-overlay's), "Developing" and "Documentation" headings with `{{...}}` bodies, installer-never-loads note. `CHANGELOG.md`: Common Changelog header + `## 0.1.0 - {{YYYY-MM-DD}}` / `### Added` / `- Initial release: {{summary}}.` `SKILL.md`: frontmatter block (`name`, `description` placeholders) + Overview/Usage headings.

- [ ] **Step 2: Update docs** — `docs/README.md` Contents row for `templates/plugin/`; root `README.md` artifact-inventory row; root `CHANGELOG.md` Unreleased→Added entry.

- [ ] **Step 3: Verify** — `rg -L '{{' docs/templates/plugin/ -l` lists all five files (every skeleton carries markers); `claude plugin validate .` still passes (templates live under `docs/`, not `plugins/`, so the marketplace is untouched).

- [ ] **Step 4: Commit**

```bash
git add docs/templates/plugin docs/README.md README.md CHANGELOG.md
git commit -m "docs: add new-plugin template skeleton"
```

---

### Task 4: hook changelog routing + test

**Files:**
- Modify: `scripts/hooks/pre-commit-check.sh`, `scripts/hooks/README.md`, `scripts/README.md`, `README.md`, `CHANGELOG.md`
- Test: `scripts/hooks/tests/pre-commit-check-test.sh` (create; check for an existing test dir first and colocate with it if one exists)

**Interfaces:**
- Consumes: `plugins/<name>/CHANGELOG.md` created in Task 1; routing rule text from Task 2.

- [ ] **Step 1: Write the failing test** — a bash script that builds a throwaway git repo in `mktemp -d`, copies `pre-commit-check.sh` in, creates tracked `README.md`, `CHANGELOG.md`, `plugins/demo/CHANGELOG.md`, `plugins/demo/file.txt` on a work branch, and asserts four cases:

```bash
#!/usr/bin/env bash
set -euo pipefail
hook="$(cd "$(dirname "$0")/.." && pwd)/pre-commit-check.sh"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cd "$tmp"; git init -q; git checkout -qb work
mkdir -p plugins/demo
printf 'x\n' > README.md; printf 'x\n' > CHANGELOG.md
printf 'x\n' > plugins/demo/CHANGELOG.md; printf 'x\n' > plugins/demo/file.txt
git add README.md CHANGELOG.md plugins/demo/CHANGELOG.md plugins/demo/file.txt
git -c user.email=t@t -c user.name=t commit -qm init

fail=0
check() { # $1=expect(0|1) $2=name; stdin: files to stage
  git reset -q
  while read -r f; do [ -n "$f" ] && printf 'y\n' >> "$f" && git add "$f"; done
  if "$hook" >/dev/null 2>&1; then got=0; else got=1; fi
  git checkout -q -- .; git reset -q
  [ "$got" = "$1" ] || { echo "FAIL: $2 (expected $1, got $got)"; fail=1; }
}
check 1 "plugin change without plugin changelog" <<< "plugins/demo/file.txt"
check 0 "plugin change with plugin changelog" <<< $'plugins/demo/file.txt\nplugins/demo/CHANGELOG.md'
check 1 "root change without root changelog" <<< $'file-at-root.txt'  # created below
printf 'x\n' > file-at-root.txt; git add file-at-root.txt; git -c user.email=t@t -c user.name=t commit -qm add
check 1 "root change without root docs" <<< "file-at-root.txt"
check 0 "root change with root docs" <<< $'file-at-root.txt\nREADME.md\nCHANGELOG.md'
exit "$fail"
```

  (Adjust ordering so `file-at-root.txt` is committed before the checks that stage it; drop the duplicated third check when writing the real file. `shellcheck` both scripts.)

- [ ] **Step 2: Run it, verify it fails** — `bash scripts/hooks/tests/pre-commit-check-test.sh`; expected FAIL on "plugin change without plugin changelog" (current hook demands root docs instead) — confirming the test detects the old behavior.

- [ ] **Step 3: Modify the hook.** In `pre-commit-check.sh`, replace the root README/CHANGELOG block (lines 17–30) with routing:

```bash
# Split staged files: plugin-internal vs repo-level (root README/CHANGELOG exempt).
nondoc=$(grep -vxE 'README\.md|CHANGELOG\.md' <<<"$staged" || true)
repo_level=$(grep -vE '^plugins/[^/]+/' <<<"$nondoc" || true)
plugin_names=$(grep -oE '^plugins/[^/]+/' <<<"$nondoc" | sort -u | cut -d/ -f2 || true)

if [ -n "$repo_level" ]; then
  if ! grep -qx 'README.md' <<<"$staged"; then
    echo "error: this commit changes repo-level files but does not update README.md." >&2
    echo "fix: update README.md in the same commit and stage it." >&2
    exit 1
  fi
  if ! grep -qx 'CHANGELOG.md' <<<"$staged"; then
    echo "error: this commit changes repo-level files but does not update CHANGELOG.md." >&2
    echo "fix: add a Common Changelog entry in the same commit and stage it." >&2
    exit 1
  fi
fi

for name in $plugin_names; do
  cl="plugins/${name}/CHANGELOG.md"
  if ! grep -qx "$cl" <<<"$staged"; then
    echo "error: this commit changes plugins/${name}/ but does not update ${cl}." >&2
    echo "fix: add a Common Changelog entry to ${cl} and stage it." >&2
    exit 1
  fi
done
```

  Note `plugins/README.md` itself matches neither `^plugins/[^/]+/` nor root-doc exemption — it lands in `repo_level`, which is correct (it is a repo-level file). Keep the Directory Guide and general folder-README loops unchanged, but drop `plugins/<name>/CHANGELOG.md` staging from triggering its own plugin-changelog demand (staging only a plugin changelog is a plugin-internal commit that already satisfies the rule: `nondoc` includes it, `plugin_names` finds it, `grep -qx` passes).

- [ ] **Step 4: Run test + linters, verify pass** — `bash scripts/hooks/tests/pre-commit-check-test.sh` exits 0; `shellcheck scripts/hooks/pre-commit-check.sh scripts/hooks/tests/pre-commit-check-test.sh`; `shfmt -d` both.

- [ ] **Step 5: Update docs** — `scripts/hooks/README.md` and `scripts/README.md` describe the routing + test; root `README.md` artifact inventory (test path); root `CHANGELOG.md` Unreleased→Changed entry.

- [ ] **Step 6: Commit** (this commit touches repo-level files, so old and new rules agree):

```bash
git add scripts/hooks/pre-commit-check.sh scripts/hooks/tests/pre-commit-check-test.sh \
  scripts/hooks/README.md scripts/README.md README.md CHANGELOG.md
git commit -m "chore(hooks): route changelog checks per plugin"
```

---

### Task 5: PR

- [ ] **Step 1:** `git fetch origin && git log origin/main..HEAD --oneline`, push branch, `gh pr create` (plain factual body describing the four commits; no banned words).
- [ ] **Step 2:** Wait for the CodeRabbit walkthrough comment (`gh pr view <n> --comments`); treat pre-merge-check warnings as findings.
- [ ] **Step 3:** Ask the user before merging; delete the branch after merge.
