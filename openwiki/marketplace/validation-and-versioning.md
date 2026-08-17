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
directory). The root [`README.md`](/README.md) lists this as a Development command, and the
root [`CLAUDE.md`](/CLAUDE.md) Desired outcome states plainly: "Each plugin passes
`claude plugin validate .` before release." Release history (what shipped and when) lives in
`CHANGELOG.md` and each plugin's own `version`, not in a README status section.

CodeRabbit's `**/.claude-plugin/*.json` path instruction (see
[code review](../governance/code-review.md)) performs a lighter-weight version of the same
check during PR review — confirming valid JSON, a semver `version`, and a marketplace entry
for every plugin directory — but `claude plugin validate .` is the authoritative, pre-release
gate.

## The shipping-file version-bump rule

A **shipping file** is any tracked file a user actually receives when they install a plugin.
The root [`CLAUDE.md`](/CLAUDE.md) names the set explicitly: `plugin.json`, `SKILL.md`, and
everything under `commands/`, `skills/`, `agents/`, `helpers/`, and `references/` — including
their folder `README.md` files. `commands/` was added to this list alongside the new
`/sec-overlay:audit` command, since a `commands/*.md` file is install payload and, without the
bump, the update mechanism never ships a change to it. A plugin's own `CLAUDE.md` (its
**operating manual**, read only when working *inside* the plugin/skill) is explicitly **not** a
shipping file: editing it alone does not bump the version. This distinction is restated in the
skill's own [`README.md`](/plugins/sec-overlay/skills/sec-overlay/README.md) ("Version bumps are
automatic").

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

The plugin's `plugin.json` currently reads `"version": "1.37.2"` — the accumulated result of
this rule applied across every shipping-file-touching commit since the plugin's initial
release; see `plugins/sec-overlay/CHANGELOG.md` for the per-version history.

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

Because CodeRabbit's pre-merge checks are advisory (`request_changes_workflow: false` —
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
