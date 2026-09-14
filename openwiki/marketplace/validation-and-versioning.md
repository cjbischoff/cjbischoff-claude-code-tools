---
type: process-guide
title: Plugin Validation and the Semver Version-Bump Rule
description: How to validate a plugin and marketplace manifest before release, and the Conventional-Commits-driven rule for bumping a plugin's version, including which mechanism actually enforces it.
tags: [marketplace, versioning, semver, plugin-json, validation]
---

# Plugin validation and versioning

## Validating manifests

Before any release, run:

```bash
claude plugin validate .
```

from the repository root. This is the Claude Code CLI's own manifest validator — it checks
`.claude-plugin/marketplace.json` and every plugin's `.claude-plugin/plugin.json` for schema
correctness (valid JSON, required fields present, a marketplace entry existing for each plugin
directory). The root [`README.md`](/README.md) lists this as the first Development command,
and the root [`CLAUDE.md`](/CLAUDE.md) Desired outcome states plainly: "Each plugin passes
`claude plugin validate .` before release." As of this writing the repository's Status section
records that "plugin and marketplace manifests validate."

CodeRabbit's `**/.claude-plugin/*.json` path instruction (see
[code review](../governance/code-review.md)) performs a lighter-weight version of the same
check during PR review — confirming valid JSON, a semver `version`, and a marketplace entry
for every plugin directory — but `claude plugin validate .` is the authoritative, pre-release
gate.

## The shipping-file version-bump rule

A **shipping file** is any tracked file a user actually receives when they install a plugin.
For `sec-overlay` that is: `.claude-plugin/plugin.json`, `SKILL.md`, and everything under
`commands/`, `skills/`, `agents/`, `helpers/`, and `references/` — including their folder
`README.md` files. `commands/` (the `/sec-overlay:audit` slash command — see
[the review pipeline](../plugins/sec-overlay/review-pipeline.md)) was added to this list after
the root `CLAUDE.md` recognized that a plugin-root slash-command file is install payload just
like a skill file: without the bump the update mechanism never ships a `commands/` change. A
plugin's own `CLAUDE.md` (its **operating manual**, read only when working *inside* the skill)
is explicitly **not** a shipping file: editing it alone does not bump the version. This
distinction is stated identically in the root [`CLAUDE.md`](/CLAUDE.md) Conventions section and
the skill's own [`CLAUDE.md`](/plugins/sec-overlay/skills/sec-overlay/CLAUDE.md) §1.

The rule: **a commit that changes a shipping file in a plugin must bump that plugin's
`version` in the same commit**, using the commit's own Conventional Commit type to pick the
semver increment:

| Commit type / marker | Bump |
|---|---|
| `!` after type/scope, or a `BREAKING CHANGE:` footer | major |
| `feat` | minor |
| any other type (`fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`) | patch |

The edit lands in `plugins/<name>/.claude-plugin/plugin.json`'s `version` field, in the same
commit as the shipping-file change. `marketplace.json` never needs an edit for this — it does
not pin plugin versions.

As a concrete example of the rule being applied: the plugin's `plugin.json` is currently at a
major version (`2.x`), not a `1.x` or `0.x` release. The jump to `2.0.0` happened when a defect
repair deleted the unreachable `factcheck` phase, its CLI module, its agent prompt, and its
`fact-checked` verification-enum value together — each surface was externally reachable (a
caller of `factcheck.py`, a workspace carrying the enum value, a schema validator pinned to it),
so semver's answer to removing a public surface is a major bump, recorded with a `BREAKING
CHANGE:` commit footer and explained in
[`docs/decisions/2026-09-01-sec-overlay-major-version-bump.md`](/docs/decisions/2026-09-01-sec-overlay-major-version-bump.md).
Most day-to-day changes are much smaller: a `feat` commit accumulates a minor bump, everything
else accumulates a patch bump.

## Where this rule is (and is not) enforced — important nuance

Unlike the [doc-update-guard and commit-message hooks](../governance/hooks-and-commits.md),
**the version-bump rule is not checked by a pre-commit hook.** Searching
`scripts/hooks/pre-commit-check.sh` and `scripts/hooks/commit-msg-check.sh` turns up no
reference to `plugin.json` or `version` at all — a commit that changes a sec-overlay shipping
file without touching `plugin.json`'s `version` will pass both hooks and the GitHub ruleset on
`main` without complaint.

The rule is instead declared as **policy** in the root README's Governance section and root
`CLAUDE.md`'s Conventions section, and checked only by CodeRabbit's `plugin-version-bump`
pre-merge check, which runs in `warning` mode (`.coderabbit.yaml`):

> FAIL if a shipping file changed under `plugins/<name>/` and the `version` field in
> `plugins/<name>/.claude-plugin/plugin.json` is unchanged. FAIL if the version increment does
> not match the PR's Conventional Commit type... PASS if only `plugins/<name>/CLAUDE.md`
> changed, which is an operating manual and not a shipping file.

The check's own shipping-file definition (`.claude-plugin/plugin.json`, `SKILL.md`,
`skills/`/`agents/`/`helpers/`/`references/`) has not yet been updated to name `commands/`
alongside them — the root `CLAUDE.md`'s policy statement is the more current source for that
folder's inclusion. Because CodeRabbit's pre-merge checks are advisory (`request_changes_workflow: false` —
see [code review](../governance/code-review.md)), the GitHub ruleset requiring a pull request
is the only *required* gate on `main`; a missed version bump surfaces as a CodeRabbit warning
comment, not a blocked merge. Treat that warning as a real finding — the root `README.md`
states explicitly that "Pre-merge checks mirror the governance rules above in `warning` mode,
so a violation shows up in the review as well as in the hooks" for the *other* governance
rules, but the version-bump rule specifically has no hook counterpart at all; CodeRabbit is its
only automated check.

## Related pages

- [Marketplace overview](overview.md) — manifest structure and the plugin-directory boundary.
- [Commit governance](../governance/hooks-and-commits.md) — what the pre-commit hooks *do*
  enforce mechanically.
- [Code review](../governance/code-review.md) — the full CodeRabbit configuration, including
  every pre-merge check in warning mode.
