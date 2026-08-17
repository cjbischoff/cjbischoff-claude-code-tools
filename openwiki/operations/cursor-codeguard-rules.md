---
type: reference
title: Cursor CodeGuard Rule
description: The single remaining always-applied Cursor secure-coding rule under .cursor/rules — no-hardcoded-credentials — after the marketplace dropped its twenty other CodeGuard rule files as unused.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rule

[`.cursor/rules/`](/.cursor/rules/) now holds exactly **one** file:
[`codeguard-1-hardcoded-credentials.mdc`](/.cursor/rules/codeguard-1-hardcoded-credentials.mdc).
Twenty other `codeguard-*.mdc` files — three always-applied (`codeguard-1-crypto-algorithms.mdc`,
`codeguard-1-digital-certificates.mdc`) and eighteen glob-matched, domain-scoped rules — were
removed as unused (`chore(cursor): drop unused CodeGuard rules`). Earlier revisions of this page
described a 21-file, two-tier family; that family no longer exists in this repository.

## The remaining rule

`codeguard-1-hardcoded-credentials.mdc` carries `alwaysApply: true`, meaning Cursor considers it
for every file regardless of language or glob. Its `rule_id` (`codeguard-1-hardcoded-credentials`)
matches its filename, per the same convention the removed rules followed. It states: never store
secrets, passwords, API keys, tokens, or other credentials directly in source, and lists
recognizable secret formats to actively scan for (AWS keys, Stripe keys, Google API keys, GitHub
tokens, JWTs, PEM key blocks, credentialed connection strings). This page summarizes it; see the
file itself for the exact guidance.

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) still audits changed files under both
`references/codeguard/` and `.cursor/rules/` together whenever either changes, checking that
every rule names a concrete replacement for whatever it forbids and that no `rule_id` collides
across files — that check's instructions were not narrowed when the other twenty files were
removed, so it still applies to this one remaining file and to any rule added back later.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md) — seven domain-scoped markdown checklists
consumed by the harness's own `patch`/`triage` agents to pick a correct remediation shape, and by
`citations.py` to stamp advisory CodeGuard ids onto findings. Those are a different artifact from
the single `.cursor/rules/` file on this page: `.cursor/rules/` is a Cursor-editor rule applied
while a human or agent edits code in *this* repository (or a target repository a plugin ships it
into); `references/codeguard/` is data the sec-overlay harness's own prompts load at
investigation/patch time. CodeRabbit's `codeguard-reference-audit` check is the one place both
are cross-checked together for `rule_id` consistency.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto/CVSS policy.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
