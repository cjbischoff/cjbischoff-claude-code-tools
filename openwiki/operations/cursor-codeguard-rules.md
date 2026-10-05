---
type: reference
title: Cursor CodeGuard Rules
description: The single always-applied Cursor secure-coding rule under .cursor/rules — a no-hardcoded-credentials check — and how it differs from the sec-overlay plugin's own references/codeguard/ checklists.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rules

[`.cursor/rules/`](/.cursor/rules/) holds **one** `codeguard-*.mdc` file today:
[`codeguard-1-hardcoded-credentials.mdc`](/.cursor/rules/codeguard-1-hardcoded-credentials.mdc).
It is a secure-coding rule that Cursor applies while editing code in this repository (and, when
a plugin ships rules like it, in a target it edits). Its frontmatter carries a `rule_id`
matching its filename, a `description`, `globs: **/*`, and `alwaysApply: true` — so it is
considered for every file regardless of language.

The rule forbids storing secrets, passwords, API keys, tokens, or other credentials directly in
source, and lists recognizable secret formats to actively scan for (AWS keys, Stripe keys,
Google API keys, GitHub tokens, JWTs, PEM key blocks, credentialed connection strings).

## What used to be here

An earlier version of this family had 21 files: three always-applied rules (this one, plus a
banned-crypto-algorithms rule and a certificate-validation rule) and eighteen glob-matched
domain rules (authentication, authorization, API/web services, input validation, and so on). The
twenty other files were removed; only the hardcoded-credentials rule remains tracked under
`.cursor/rules/` in the current repository. If a future change reintroduces more rules here,
update this page to describe the restored families rather than assuming this single-rule state
is permanent.

## CodeRabbit still cross-checks this file

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) still audits changed files under
`references/codeguard/` and `.cursor/rules/` together, checking that every rule names a concrete
replacement for whatever it forbids and that no `rule_id` collides across files
(`.coderabbit.yaml`'s `finishing_touches.custom` block). This mechanism is unchanged even though
only one file currently lives on the `.cursor/rules/` side of that check.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists consumed by the harness's own `patch`/`triage` agents to
pick a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
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
