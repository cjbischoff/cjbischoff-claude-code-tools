---
type: process-guide
title: Repository Security Automation
description: The GitHub-native and workflow-based security controls protecting this marketplace repository — dependency review, Dependabot, CodeQL default setup, secret scanning, SHA-pinned Actions, and the least-privilege workflow token.
tags: [operations, security-automation, dependency-review, dependabot, codeql, github-actions]
---

# Repository security automation

This repository layers several GitHub-native and workflow-based controls on top of
[commit governance](../governance/hooks-and-commits.md) and
[CodeRabbit review](../governance/code-review.md). This page describes what each control does
and why; it does not reproduce the YAML.

## Dependency review

`.github/workflows/dependency-review.yml` runs GitHub's `dependency-review-action` on every
pull request against `main`. It diffs the dependency manifests changed by the PR and fails the
check if any newly introduced dependency has a known vulnerability at or above `high` severity
(`fail-on-severity: high`). This is a pre-merge gate specifically for *new* vulnerable
dependencies, distinct from Dependabot's ongoing scanning below. The job's `permissions:
contents: read` is the least-privilege default this repository uses everywhere a workflow does
not need to write (see [the read-only token pattern](#the-default-read-only-workflow-token)
below).

## Dependabot

`.github/dependabot.yml` configures two weekly update streams, each opening its own PRs with a
`chore` commit-message prefix (matching this repo's [Conventional Commits](../governance/hooks-and-commits.md)
convention):

- **`github-actions`**, directory `/` — keeps every pinned Action's SHA current.
- **`pip`**, directory `/plugins/sec-overlay/skills/sec-overlay/helpers` — keeps the sec-overlay
  skill's *dev* dependencies (pytest, ruff, ty) current; recall from
  [helpers](../plugins/sec-overlay/helpers.md) that the runtime core itself declares no
  dependencies to update.

Both run on a weekly schedule rather than continuously, trading immediacy for a bounded review
burden.

## CodeQL default setup

`.github/codeql/codeql-config.yml` exists, but **no CodeQL workflow file does** — this is
deliberate, not an omission. GitHub's CodeQL "default setup" is a repository *setting*
(configured in the GitHub UI, not a checked-in `.yml`) that runs CodeQL scanning automatically
using GitHub-managed infrastructure, without a workflow file to maintain. The one file this
repository does check in only narrows what default setup analyzes:

```yaml
paths-ignore:
  - "**/fixtures/**"
  - "**/.venv/**"
  - "**/__pycache__/**"
  - "**/.pytest_cache/**"
  - "**/.ruff_cache/**"
```

This keeps CodeQL from spending analysis budget on the intentionally vulnerable detector
fixtures (see [sec-overlay overview](../plugins/sec-overlay/overview.md) — those fixtures exist
to exercise the harness's own detectors and are excluded from review and from this wiki, same
as `.openwikiignore`'s rationale) and local caches. If you are looking for "the CodeQL
workflow," there isn't one to find — the exclusion list above is the entire repo-tracked
configuration surface for it.

## Secret scanning

GitHub secret scanning and push protection are native platform features for public
repositories; they scan every push for recognizable credential patterns and can block a push
that would introduce one. Like CodeQL default setup, this is a repository setting rather than a
file in this repository — there is no workflow or config file to cite for it beyond noting it
is enabled, consistent with this being a public repository whose [`SECURITY.md`](/SECURITY.md)
directs vulnerability reports to GitHub's private advisory flow rather than public issues.

## SHA-pinned Actions

Every third-party Action reference in this repository's workflows is pinned to a full commit
SHA with the human-readable version in a trailing comment, e.g.:

```yaml
uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
```

This appears in both `dependency-review.yml` and `.github/workflows/openwiki-update.yml` (see
[OpenWiki refresh](openwiki-refresh.md)). Pinning to a SHA rather than a mutable tag (`@v7`)
means a compromised or force-pushed tag on the upstream Action cannot silently change what runs
in this repository's CI — the only way to update is a new commit that changes the SHA, which
Dependabot's `github-actions` stream (above) proposes automatically. CodeRabbit's
`.github/workflows/**` path instruction (see [code review](../governance/code-review.md)) also
checks this on every PR that touches a workflow file.

## The default read-only workflow token

Both workflows declare `permissions` explicitly rather than relying on the default:
`dependency-review.yml` uses `permissions: contents: read` — it only needs to check out code
and read manifests. `openwiki-update.yml` needs to open a pull request, so it declares the
narrower elevated grant its job actually needs (`contents: write`, `pull-requests: write`) at
the job level rather than repository-wide, and otherwise defaults to `permissions: {}` at the
workflow level. This least-privilege pattern — read-only unless a job specifically needs to
write — limits what a compromised or buggy workflow step could do even if it were tricked into
running attacker-controlled code.

## Related pages

- [Commit governance](../governance/hooks-and-commits.md) and
  [Code review](../governance/code-review.md) — the non-GitHub-native controls layered on top
  of these.
- [OpenWiki refresh](openwiki-refresh.md) — the one workflow in this repository that needs
  elevated (write) permissions, and why.
- [sec-overlay overview](../plugins/sec-overlay/overview.md) — the fixtures CodeQL and
  CodeRabbit both exclude.

