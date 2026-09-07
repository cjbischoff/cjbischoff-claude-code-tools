---
type: reference
title: Cursor CodeGuard Rules
description: The single always-applied Cursor secure-coding rule tracked under .cursor/rules — bans hardcoded credentials and secrets in source — and how it is audited alongside the sec-overlay plugin's own separate codeguard checklists.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rules

[`.cursor/rules/`](/.cursor/rules/) currently tracks exactly **one** file:
[`codeguard-1-hardcoded-credentials.mdc`](/.cursor/rules/codeguard-1-hardcoded-credentials.mdc)
(verified by directory listing and by the root `README.md`'s Artifact inventory table, which
names only this file). Earlier releases of this repository carried a larger family of 21
`codeguard-*.mdc` files (three always-applied, eighteen glob-matched by security domain); the
other 20 were removed from this repository's tracked source over the course of the sec-overlay
v5.x work. This page describes what remains, not that earlier, larger set.

## The one always-applied rule

`codeguard-1-hardcoded-credentials.mdc` carries `alwaysApply: true` (frontmatter also declares
`rule_id: codeguard-1-hardcoded-credentials`, matching its filename), so it applies to every
file Cursor edits regardless of language:

- Never store secrets, passwords, API keys, tokens, or other credentials directly in source.
- Treats the codebase as public and untrusted — any credential that appears in source is
  compromised.
- Names recognizable secret formats to actively scan for: AWS keys (`AKIA`/`AGPA`/…), Stripe
  keys (`sk_live_`/`pk_live_`/…), Google API keys (`AIza…`), GitHub tokens
  (`ghp_`/`gho_`/`ghu_`/…), JWTs (three base64 sections, `eyJ` prefix), PEM private-key blocks,
  and credentialed connection strings (`mongodb://user:pass@host`).
- Also flags warning-sign variable names (`password`, `secret`, `key`, `token`, `auth`) and
  long random-looking strings near authentication code.

This is philosophically aligned with, but independent of, the sec-overlay harness's own
`secrets.py` detector and its machine-checked
[`approved-crypto-algorithms.yaml`](../plugins/sec-overlay/references.md#machine-checked-policy-and-schemas) —
the Cursor rule guides a human or agent editing code in *this* repository (or wherever a plugin
ships it), while the harness's detector and crypto policy are what the audit pipeline itself
checks a *target* codebase against. They do not share code or configuration.

## CodeRabbit's `codeguard-reference-audit` check

Still active and unchanged in `.coderabbit.yaml` (see [code review](../governance/code-review.md)),
this finishing-touch check audits any *changed* file under both `references/codeguard/` (the
sec-overlay plugin's own checklists — see
[sec-overlay references](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing))
and `.cursor/rules/` together: it checks that every rule document's `rule_id` matches its
filename, states whether a pattern is banned or merely deprecated, names a concrete replacement
for anything it forbids, and that no `rule_id` collides across files. With only one file left
under `.cursor/rules/`, this check now has a much smaller reference surface than its
instructions (written for the larger set) imply, but nothing about the check itself changed —
it still runs against whatever `.mdc` files are present on a given PR.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists consumed by the harness's own `patch`/`investigate`
agents to pick a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard
ids onto findings. Those are a different artifact from the `.cursor/rules/` file on this page:
`.cursor/rules/` is a Cursor-editor rule applied while a human or agent edits code in this
repository; `references/codeguard/` is data the sec-overlay harness's own prompts load at
investigation/patch time. The `codeguard-reference-audit` check above is the one place both are
cross-checked together for `rule_id` consistency.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
