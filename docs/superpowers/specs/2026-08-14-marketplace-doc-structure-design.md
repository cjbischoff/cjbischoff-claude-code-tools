# Marketplace documentation structure — design

Date: 2026-08-14
Status: approved by user (interview 2026-08-14); implementation pending

## Goal

Separate marketplace-level guidance from plugin-level guidance so that:

- The root `CLAUDE.md` governs marketplace development and new-plugin scaffolding.
- Each plugin carries its own maintainer `CLAUDE.md`, user `README.md`, and `CHANGELOG.md`.
- No governance rule is stated in more than one place.

## Verified facts that shape the design

Source: code.claude.com/docs (memory, plugins, plugins-reference, plugin-marketplaces).

1. A `CLAUDE.md` at a plugin root is not loaded as context in a consuming session.
   Plugins contribute context through skills, agents, and hooks only.
2. A subdirectory `CLAUDE.md` loads only when Claude reads files under the current
   working directory. The plugin cache is never under a user's working directory,
   so no plugin `CLAUDE.md` auto-loads for installers. `SKILL.md` can point to a
   companion file, and the consuming agent can read it on demand.
3. Anthropic recommends a `README.md` and a `CHANGELOG.md` per plugin, and an
   explicit semver `version` in `plugin.json`; users receive updates only on a
   version bump.
4. Target under 200 lines per `CLAUDE.md` file for adherence.

## Decisions (from user interview)

| Topic | Decision |
|-------|----------|
| Plugin CLAUDE.md location | Both levels: `plugins/<name>/CLAUDE.md` (maintainer manual) and `skills/<skill>/CLAUDE.md` (operational companion referenced by `SKILL.md`) |
| Governance duplication | None. Plugin files link to root governance with one line; rules live only in the root `CLAUDE.md` |
| Changelogs | Per-plugin `CHANGELOG.md` keyed to plugin versions; root `CHANGELOG.md` keeps repo-level entries only. Common Changelog format everywhere |
| Plugin README | Every plugin gets a user-facing `plugins/<name>/README.md` |
| Hooks | `scripts/hooks/pre-commit-check.sh` updates in this effort: plugin-only commits require that plugin's changelog, not the root one |
| Scaffolding | Root `CLAUDE.md` gets a short "New plugin" checklist plus a `docs/templates/plugin/` skeleton to copy |
| Scope | All changes land in this session, on one branch, in sequenced commits |

## Root CLAUDE.md — target outline

1. Purpose and marketplace contract (manifest, one plugin per directory, `claude plugin validate .`).
2. Governance: branching, Conventional Commits, version-bump semver rule, CodeRabbit
   wait, changelog routing (plugin change → plugin changelog; repo change → root changelog).
3. New plugin: scaffold checklist, `docs/templates/plugin/` pointer, `marketplace.json`
   registration, validation, first changelog entry at 0.1.0.
4. Release process: bump, changelog entry, branch → PR → CodeRabbit → merge.
5. Routing rule: plugin-specific work is governed by `plugins/<name>/CLAUDE.md`;
   plugin detail never lands in the root file.
6. Decisions (kept; new decisions from this design added).
7. OpenWiki (kept; the current duplicate OpenWiki section removed).

Standing rule added: keep every `CLAUDE.md` under 200 lines.

## Per-plugin structure (sec-overlay becomes the pattern)

| File | Audience | Content |
|------|----------|---------|
| `plugins/sec-overlay/README.md` (new) | Marketplace user | What it does, install command, prerequisites, quick start, links to changelog and skill README |
| `plugins/sec-overlay/CHANGELOG.md` (new) | Marketplace user | Common Changelog for plugin versions; backfill 0.1.0 and 0.2.0 from git history |
| `plugins/sec-overlay/CLAUDE.md` (new) | Maintainer | Governance pointer (one line), developing-the-skill content (old §7), docs rules (old §8), historical notes (for example the 2026-07-31 `secrets.py` reconstruction) |
| `skills/sec-overlay/CLAUDE.md` (trimmed) | Agent running the skill | Mission (§0), environment prerequisites (§2), how to run (§3), signal architecture (§4), artifacts (§5), references (§6). Old §1, §7, §8 removed |
| `skills/sec-overlay/README.md` (edited) | Deep-dive reader | Links repointed to the split files; content otherwise unchanged |

## Template — `docs/templates/plugin/`

Five skeleton files with `{{PLACEHOLDER}}` markers:

- `.claude-plugin/plugin.json`
- `README.md`
- `CLAUDE.md`
- `CHANGELOG.md`
- `skills/{{skill-name}}/SKILL.md`

No `agents/`, `helpers/`, or `references/` stubs; those are added when a plugin
needs them.

## Hook changes — `scripts/hooks/pre-commit-check.sh`

- A commit that stages files under `plugins/<name>/` must also stage
  `plugins/<name>/CHANGELOG.md`.
- A plugin-only commit no longer requires the root `CHANGELOG.md`.
- A commit that stages files outside `plugins/` keeps the current root
  `README.md` + `CHANGELOG.md` requirement.
- Folder-README and version-bump rules are unchanged.
- The hook change ships with an invocation test in the same commit.

## Commit sequence (branch `docs/claude-md-marketplace-20260814`)

1. `docs(sec-overlay)`: plugin-root README, CHANGELOG, CLAUDE.md; trim the skill
   CLAUDE.md; repoint skill README links. Patch version bump (skill CLAUDE.md is
   a shipping file).
2. `docs`: root CLAUDE.md rewrite; root README and CHANGELOG updates.
3. `docs`: `docs/templates/plugin/` skeleton.
4. `chore(hooks)`: pre-commit script update plus test.
5. Open PR, wait for the CodeRabbit walkthrough, merge on user approval.

Commits 1–3 run under the current hook rules (root README + CHANGELOG staged
each time); commit 4 switches routing.

## Out of scope

- Plugin functionality changes.
- OpenWiki regeneration (the scheduled workflow picks the changes up).
- Backfilling the missing `docs/README.md` row for the 2026-08-11 kb-redesign
  spec (pre-existing gap, noted for a separate fix).
