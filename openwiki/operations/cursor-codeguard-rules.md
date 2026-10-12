---
type: reference
title: Cursor CodeGuard Rule
description: The single always-applied Cursor secure-coding rule under .cursor/rules — banning hardcoded credentials — and how it differs from the sec-overlay plugin's own references/codeguard/ checklists.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rule

[`.cursor/rules/`](/.cursor/rules/) holds one `codeguard-*.mdc` file today:
[`codeguard-1-hardcoded-credentials.mdc`](/.cursor/rules/codeguard-1-hardcoded-credentials.mdc) — a
secure-coding rule Cursor applies while editing code in this repository. Its frontmatter carries
`alwaysApply: true` and `globs: **/*`, so it is considered for every file regardless of language,
plus a `rule_id` (`codeguard-1-hardcoded-credentials`) matching its filename. This repository
previously shipped a larger family of 21 `codeguard-*.mdc` files (three always-applied, eighteen
glob-matched per security domain); all but this one were removed. Root `README.md`'s artifact
inventory lists the file directly rather than a family table, confirming the current scope.

## What the rule does

**`codeguard-1-hardcoded-credentials.mdc`** — never store secrets, passwords, API keys, tokens,
or other credentials directly in source; treats the codebase as public and untrusted, and lists
recognizable secret formats to actively scan for (AWS keys, Stripe keys, Google API keys, GitHub
tokens, JWTs, PEM key blocks, credentialed connection strings). It also requires the agent
explain how and why the rule was applied whenever it fires.

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) still audits changed files under
`references/codeguard/` and `.cursor/rules/` together, checking that every rule names a concrete
replacement for whatever it forbids and that no `rule_id` collides across files — that check's
configuration in `.coderabbit.yaml` is unchanged by the rule-set shrink; it simply has one file
instead of 21 to reconcile against the sec-overlay plugin's own checklist folder on each PR.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists consumed by the harness's own `patch`/`triage` agents
to pick a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
findings. Those are a different artifact from the `.cursor/rules/` file on this page: the
`.cursor/rules/` file is a Cursor-editor rule applied while a human or agent edits code in *this*
repository (or a target repository a plugin ships it into); `references/codeguard/` is data the
sec-overlay harness's own prompts load at investigation/patch time. CodeRabbit's
`codeguard-reference-audit` check is the one place both are cross-checked together for `rule_id`
consistency.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
