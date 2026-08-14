# cjbischoff-claude-code-tools

## Purpose

This workspace is a Claude Code plugin marketplace. It distributes personal plugins for Christopher Bischoff.

## Desired outcome

- A valid marketplace manifest at `.claude-plugin/marketplace.json`.
- One plugin per directory under `plugins/`.
- Each plugin passes `claude plugin validate .` before release.

## Governance

Every change to a tracked file goes through a branch and a Conventional Commits message. Direct commits to `main` are not permitted, including by an agent. Hooks enforce these rules (`prek install` activates them).

- Direct pushes to `main` are also blocked on GitHub by a repository ruleset (pull request required; force-push and deletion blocked).
- **Branch naming:** `<type>/<short-kebab-description>`, e.g. `feat/poc-reproducer-retry`, `fix/hook-grace-period`.
- **Commit types:** `feat` · `fix` · `chore` · `docs` · `style` · `refactor` · `perf` · `test`.
- **Message format:** `<type>(<optional-scope>): <imperative summary, under 50 chars>`, optional body wrapped at 72 chars explaining why, optional footer.
- **Breaking changes** to a plugin's contract or a script's CLI: `!` after the type/scope plus a `BREAKING CHANGE:` footer.
- Merge the branch into `main` when the change is verified; delete the branch after merge.
- **Changelog routing:** a commit whose changes are all inside `plugins/<name>/` updates that plugin's `CHANGELOG.md` (and its `plugin.json` version when shipping files change). A commit touching anything outside `plugins/` updates the root `CHANGELOG.md` and root `README.md`. Mixed commits do both.
- Every folder in the README.md Directory Guide has its own `README.md`. A commit that changes a tracked file inside `scripts/` or `docs/` must update that folder's README.md in the same commit. Inside `plugins/`, a commit updates the immediate folder's `README.md` (`plugins/<name>/README.md`, or a nested skill/helper folder's README.md) instead of `plugins/README.md`, and a plugin-internal commit updates the plugin's `CHANGELOG.md` instead of the root docs.
- Bump a plugin's `version` automatically, in the same commit that changes a **shipping file** in that plugin. A shipping file is any tracked file a user receives on install: `plugin.json`, `SKILL.md`, and everything under `skills/`, `agents/`, `helpers/`, and `references/`, including their folder `README.md` files. A plugin `CLAUDE.md` (operating manual) is **not** a shipping file; editing one alone does not bump.
- Derive the increment from the commit's Conventional Commit type with semver: a breaking change (`!` or `BREAKING CHANGE:`) bumps major, `feat` bumps minor, and every other type (`fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`) bumps patch. Edit `version` in the plugin's `.claude-plugin/plugin.json` in the same commit. `marketplace.json` does not pin versions, so it needs no edit.
- Keep every CLAUDE.md under 200 lines.
- Plugin skills keep all executable logic under `skills/<name>/scripts/`, not in SKILL.md.
- Scripts must not reference paths outside their plugin directory. Only the plugin directory is copied to the plugin cache on install.

### Waiting for the CodeRabbit review

CodeRabbit reviews every pull request against `main`, but a review takes a few minutes. Merging sooner than that wastes the review; the first three pull requests on this repo merged so fast that CodeRabbit reported `Review failed — the pull request is closed` and produced no findings.

- Open the pull request, then wait for CodeRabbit's walkthrough comment before merging. `gh pr view <n> --comments` shows whether the review landed.
- CodeRabbit does not gate the merge (`request_changes_workflow: false`), so nothing blocks an early merge except this rule.
- `abort_on_close: false` lets an in-flight review finish even if the pull request merges first, so a late merge still produces findings — they just arrive after the fact.
- Automatic incremental reviews pause after 2 reviewed commits to conserve the open-source rate limit. Comment `@coderabbitai review` to request another pass, or `@coderabbitai rate limit` to check remaining capacity.
- Pre-merge checks run in `warning` mode and restate this repo's governance (README and CHANGELOG updated, plugin version bumped, folder README updated, no paths outside a plugin). Treat a warning as a real finding: it means a hook would have caught the same thing.

## New plugin

To add a plugin:

1. Copy `docs/templates/plugin/` to `plugins/<name>/`.
2. Replace every `{{PLACEHOLDER}}` marker with the plugin's real values.
3. Register the plugin in `.claude-plugin/marketplace.json`.
4. Run `claude plugin validate .`.
5. Write the first entry in the plugin's `CHANGELOG.md` at version `0.1.0`.

## Release process

1. Bump `plugin.json`'s semver by the commit's Conventional Commit type (see Governance).
2. Add an entry to the plugin's `CHANGELOG.md`.
3. Branch, open a pull request, wait for CodeRabbit's walkthrough comment, then merge on approval.
4. Users only receive updates when a version bump ships — no bump, no update.

## Routing rule

When improving an existing plugin, `plugins/<name>/CLAUDE.md` governs the specifics; plugin detail never lands in this file.

## Decisions

- `plugin.json` declares no components; the default `skills/` directory scan handles discovery, strict mode stays at its default (true).
- Plugin versions bump automatically on shipping-file changes, using Conventional-Commits semver (breaking → major, `feat` → minor, other types → patch); a plugin `CLAUDE.md` edit alone does not bump. Replaces the prior manual-bump policy.
- Governance is enforced with prek local hooks rather than convention only, per user request for forced updates.
- Do not add `.github/README.md`; GitHub would show it as the repository homepage instead of the root marketplace README.
- Per-plugin changelogs plus a plugin-root doc trio (README, CHANGELOG, CLAUDE.md) supersede a single root changelog for plugin changes.
- A plugin `CLAUDE.md` never loads for installers, so maintainer manuals are safe to keep at the plugin root.
- Every CLAUDE.md targets under 200 lines.

## OpenWiki

The generated wiki lives under `openwiki/`. `openwiki/INSTRUCTIONS.md` is the user-authored brief for `--init` and `--update`; do not rewrite it. `.openwikiignore` is a read boundary separate from `.gitignore`. Do not hand-edit generated pages unless explicitly asked; prefer updating source code/docs and letting OpenWiki regenerate. It is optional just-in-time context, not required startup reading.

First init is local: `openwiki code --init --print` with `OPENWIKI_PROVIDER=anthropic`, `OPENWIKI_MODEL_ID=claude-sonnet-5`, `OPENWIKI_TELEMETRY_DISABLED=1`, and `DO_NOT_TRACK=1`. Later refreshes use `.github/workflows/openwiki-update.yml` (needs the `ANTHROPIC_API_KEY` repository secret) or `openwiki code --update --print`. The scheduled workflow refreshes the wiki on its own schedule.

<!-- OPENWIKI:START -->

- Treat source code and tests as authoritative. A brief's unknowns and review items are verification gaps, not automatic requirements.
- Prefer the narrowest quiet validation that proves the changed behavior. Preserve complete failure output.

<!-- OPENWIKI:END -->
