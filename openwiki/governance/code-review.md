---
type: process-guide
title: CodeRabbit Pull Request Review Configuration
description: How CodeRabbit reviews every pull request against main in this repository — its comment-only role relative to the GitHub ruleset, its warning-mode pre-merge checks that mirror governance rules, and the enabled analysis tools.
tags: [governance, code-review, coderabbit, pull-requests]
---

# Code review (CodeRabbit)

CodeRabbit reviews every pull request opened against `main`, configured entirely by
[`.coderabbit.yaml`](/.coderabbit.yaml). Because this repository is public, it qualifies for
CodeRabbit's open-source plan, which grants Pro+ features without a subscription (the file's
own header comment notes Pro/Pro+ keys are "inert rather than invalid" if the plan ever drops
to Free, and `enable_free_tier: true` keeps summaries running in that case).

## Comments, never gates

CodeRabbit is explicitly **advisory only** in this repository:

```yaml
request_changes_workflow: false
fail_commit_status: false
```

Both settings point the same direction: `request_changes_workflow: false` means CodeRabbit
never requests changes as a blocking review state, and `fail_commit_status: false` means a
review with findings never turns CodeRabbit's own commit status red — so no branch-protection
rule could gate on it even if one were configured to look. Combined with `abort_on_close:
false` (below — a late merge still gets a review, it just can't stop anything), CodeRabbit has
no mechanism in this repository capable of blocking a merge. The
[GitHub ruleset on `main`](hooks-and-commits.md#the-github-ruleset-on-main) — pull request
required, no force-push/deletion — is the *only* required gate. Root `README.md`: "The review
comments but never blocks: the GitHub ruleset is the only required gate on `main`."

## Timing matters

A pull request merged within seconds of opening gets **no review at all** — the first three
pull requests on this repo merged so fast that CodeRabbit reported "Review failed — the pull
request is closed" with zero findings. Two settings shape how to work around this:

- `abort_on_close: false` — an in-flight review continues even if the PR merges first, so a
  late merge still produces findings (they simply arrive after the fact).
- `auto_pause_after_reviewed_commits: 2` — automatic incremental reviews pause after two
  reviewed commits to conserve the open-source plan's rate limit; comment `@coderabbitai
  review` to request another pass, or `@coderabbitai rate limit` to check remaining capacity.

Root `CLAUDE.md`'s guidance: open the pull request, then **wait** for CodeRabbit's walkthrough
comment before merging (`gh pr view <n> --comments` shows whether it landed).

## Pre-merge checks (warning mode) — mirrors the hooks

`.coderabbit.yaml`'s `pre_merge_checks.custom_checks` restate several governance rules from
[commit governance](hooks-and-commits.md) and
[versioning](../marketplace/validation-and-versioning.md) in `warning` mode, so a violation
that a local hook would have caught (if hooks were skipped or bypassed) still surfaces as a
review comment:

| Check | FAILs when |
|---|---|
| `readme-and-changelog-updated` | a PR changes any tracked file other than `README.md`/`CHANGELOG.md` without modifying both, or `CHANGELOG.md` changes without a new entry under an `## Unreleased` `### Changed`/`### Added`/`### Removed`/`### Fixed` group |
| `plugin-version-bump` | a shipping file changed under `plugins/<name>/` and `plugin.json`'s `version` is unchanged, or the increment doesn't match the PR's Conventional Commit type (see [versioning](../marketplace/validation-and-versioning.md) for the only-check-not-hook nuance) |
| `folder-readme-updated` | a PR changes a file in a directory with a tracked `README.md` without also updating that `README.md` |
| `no-paths-outside-plugin` | a file under `plugins/<name>/` references a path outside that plugin directory — parent-relative escape, an absolute `/Users`/`/home`/`/tmp` path, or a sibling top-level directory like `scripts/` or `docs/` |

The PR title check (also `warning` mode) requires the same Conventional Commit format as the
`commit-msg-check.sh` hook. `issue_assessment` is explicitly turned `off`: "This repo does not
track work in issues."

## Path filters and per-area review instructions

Seeded detector fixtures under `**/fixtures/**` and `**/fixtures_struct/**` are excluded from
review (`path_filters`), "so seeded findings do not bury real ones" — the same rationale
`.openwikiignore` uses to keep OpenWiki out of them. `**/uv.lock`, `**/*.sarif`, `**/*.diff`,
and cache directories are excluded too.

`path_instructions` give CodeRabbit domain-specific review criteria per area of the repository:

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/**/*.py` — determinism (no
  unseeded randomness, wall-clock reads, or set/dict-order dependence), subprocess safety (no
  `shell=True`, explicit timeouts), path handling, untrusted-input parsing, and a call-out for
  any change that "lets a finding bypass the critic or gate ladder." Concretely, this instructs
  a reviewer to flag anything that would weaken
  [`findings_gate.py`'s tool-receipt check](../plugins/sec-overlay/helpers.md#the-tool-receipt-gate) —
  for example, widening `evidence.py`'s `_MECHANICAL` set to accept an unverifiable source, or
  loosening `validate_findings`'s requirement that a `confirmed`/`fixed` finding carry at least
  one real tool receipt — since that check is exactly the mechanism this instruction protects.
- `helpers/tests/test_*.py` — both success and failure paths asserted, `tmp_path` fixtures, no
  network or binary dependence unless explicitly marked.
- `helpers/bench/**/*.py` — reproducible scoring, parameterized corpus paths.
- `scripts/hooks/**/*.sh` — `set -euo pipefail`, quoted expansions, fail-closed behavior.
- `plugins/**/SKILL.md` — flags shell pipelines that should be a script instead (executable
  logic belongs under `skills/<name>/scripts/` per repo convention) and confirms no path
  escapes the plugin directory.
- `**/.claude-plugin/*.json` — valid JSON, semver `version`, a marketplace entry per plugin.
- `.github/workflows/**` — third-party Actions pinned to a full commit SHA with a version
  comment, least-privilege `permissions`, and no untrusted PR input reaching a `run` block
  through interpolation.

Two `finishing_touches.custom` checks specifically watch the security-reference surfaces this
wiki documents: `codeguard-reference-audit` audits changed files under
`references/codeguard/` and [`.cursor/rules/`](../operations/cursor-codeguard-rules.md) for a
matching `rule_id`/filename and a named replacement for anything banned; `detector-coverage-gap`
checks that a new detector or ASVS mapping has a corresponding test under `helpers/tests/`.

## Enabled tools

`tools:` turns on `ruff` (Python; `flake8`/`pylint` disabled as redundant), `shellcheck` +
`checkmake`, `markdownlint`/`yamllint`/`dotenvLint`, `actionlint` + `zizmor` (GitHub Actions),
`gitleaks` + `trufflehog` + `semgrep` + `osvScanner` (security scanning), and `ast-grep`
essential rules — "matching this repo's own ast-grep usage" inside the sec-overlay harness (see
[helpers](../plugins/sec-overlay/helpers.md)).

## Related pages

- [Commit governance](hooks-and-commits.md) — the pre-commit hooks these checks mirror.
- [Validation and versioning](../marketplace/validation-and-versioning.md) — the version-bump
  rule this is the *only* automated check for.
- [Cursor CodeGuard rules](../operations/cursor-codeguard-rules.md) — the `.cursor/rules/`
  files the `codeguard-reference-audit` finishing-touch inspects.
