---
type: reference
title: Cursor CodeGuard Rule
description: The single always-applied Cursor secure-coding rule remaining under .cursor/rules/ — banning hardcoded credentials — and how it differs from the sec-overlay plugin's own, separate references/codeguard/ checklists and machine-checked crypto policy.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rule

[`.cursor/rules/`](/.cursor/rules/) currently holds a **single** file:
`codeguard-1-hardcoded-credentials.mdc`. It is a secure-coding rule Cursor applies while editing
code in this repository — an always-applied ban on hardcoded secrets, not a glob-matched,
domain-specific family. An earlier release of this repository shipped a much larger set here (21
`codeguard-*.mdc` files: three always-applied plus eighteen glob-matched, one per security
domain); all but this one file were removed, leaving only the credentials rule. This page
documents the current, smaller surface rather than the historical one.

## The remaining rule

`codeguard-1-hardcoded-credentials.mdc` carries `alwaysApply: true` (considered for every file
regardless of language or glob) and a `rule_id` matching its filename. It forbids storing
secrets, passwords, API keys, tokens, or other credentials directly in source, on the premise
that the codebase should be treated as public and untrusted. It lists recognizable secret
formats to actively scan for — AWS access keys (`AKIA`/`ASIA`/…), Stripe keys (`sk_live_`/
`pk_live_`/…), Google API keys (`AIza…`), GitHub tokens (`ghp_`/`gho_`/…), JWTs (`eyJ…`), and PEM
private-key blocks — plus warning-sign variable-name patterns (`password`, `secret`, `key`,
`token`, `auth`).

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) still audits changed files under both
`references/codeguard/` and `.cursor/rules/` together, checking that every rule names a concrete
replacement for whatever it forbids and that no `rule_id` collides across files — that check's
scope has not shrunk even though `.cursor/rules/` now has only one file to check.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists consumed by the harness's own `patch`/triage agents to
pick a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
findings. Those are a different artifact from the `.cursor/rules/` file on this page: the
`.cursor/rules/` rule is a Cursor-editor rule applied while a human or agent edits code in *this*
repository (or a target repository a plugin ships it into); `references/codeguard/` is data the
sec-overlay harness's own prompts load at investigation/patch time. This repository's own,
independent secrets detector (`helpers/sec_overlay/secrets.py`) and machine-checked crypto policy
(`crypto_policy.py` / `approved-crypto-algorithms.yaml`) are philosophically aligned with the
hardcoded-credentials rule above but are enforced separately, inside the harness, not by Cursor.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
