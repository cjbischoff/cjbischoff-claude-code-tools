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
`claude plugin validate .` before release." The root README no longer carries a status log —
`CHANGELOG.md` and each plugin's own `version`/`CHANGELOG.md` are the record of what shipped.

CodeRabbit's `**/.claude-plugin/*.json` path instruction (see
[code review](../governance/code-review.md)) performs a lighter-weight version of the same
check during PR review — confirming valid JSON, a semver `version`, and a marketplace entry
for every plugin directory — but `claude plugin validate .` is the authoritative, pre-release
gate.

## The shipping-file version-bump rule

A **shipping file** is any tracked file a user actually receives when they install a plugin.
For `sec-overlay` that is: `.claude-plugin/plugin.json`, `SKILL.md`, and everything under
`skills/`, `agents/`, `helpers/`, and `references/` — including their folder `README.md`
files. A plugin's own `CLAUDE.md` (its **operating manual**, read only when working *inside*
the skill) is explicitly **not** a shipping file: editing it alone does not bump the version.
This distinction is stated identically in the root [`CLAUDE.md`](/CLAUDE.md) Conventions
section and the skill's own
[`CLAUDE.md`](/plugins/sec-overlay/skills/sec-overlay/CLAUDE.md) §1.

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

As a concrete example of the rule being applied: the plugin's `plugin.json` currently reads
`"version": "1.107.3"`. That number is the accumulated result of hundreds of shipping-file
commits, each bumping major/minor/patch per its own Conventional Commit type — there is no
single release note that explains the jump; `plugins/sec-overlay/CHANGELOG.md` is the
authoritative per-release history. Do not treat a specific version number in this wiki as
current for longer than it takes to check `plugin.json` directly.

## Where this rule is (and is not) enforced — important nuance

Unlike the [doc-update-guard and commit-message hooks](../governance/hooks-and-commits.md),
**the version-bump rule is not checked by a pre-commit hook.** Searching
`scripts/hooks/pre-commit-check.sh` and `scripts/hooks/commit-msg-check.sh` turns up no
reference to `plugin.json` or `version` at all — a commit that changes a sec-overlay shipping
file without touching `plugin.json`'s `version` will pass both hooks and the GitHub ruleset on
`main` without complaint.

The rule is instead declared as **policy** in the root [`CLAUDE.md`](/CLAUDE.md)'s Governance
section, and checked only by CodeRabbit's `plugin-version-bump` pre-merge check, which runs in
`warning` mode (`.coderabbit.yaml`):

> FAIL if a shipping file changed under `plugins/<name>/` and the `version` field in
> `plugins/<name>/.claude-plugin/plugin.json` is unchanged. FAIL if the version increment does
> not match the PR's Conventional Commit type... PASS if only `plugins/<name>/CLAUDE.md`
> changed, which is an operating manual and not a shipping file.

Because CodeRabbit's pre-merge checks are advisory (`request_changes_workflow: false` —
see [code review](../governance/code-review.md)), the GitHub ruleset requiring a pull request
is the only *required* gate on `main`; a missed version bump surfaces as a CodeRabbit warning
comment, not a blocked merge. Treat that warning as a real finding — root `CLAUDE.md` says
plainly of CodeRabbit's pre-merge checks in general: "Treat a warning as a real finding: it
means a hook would have caught the same thing." The other governance rules those checks
restate (README/CHANGELOG updated, folder README updated, no paths outside a plugin) *do* have
a hook counterpart; the version-bump rule specifically does not — CodeRabbit is its only
automated check.

## Related pages

- [Marketplace overview](overview.md) — manifest structure and the plugin-directory boundary.
- [Commit governance](../governance/hooks-and-commits.md) — what the pre-commit hooks *do*
  enforce mechanically.
- [Code review](../governance/code-review.md) — the full CodeRabbit configuration, including
  every pre-merge check in warning mode.
