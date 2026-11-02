---
type: reference
title: Cursor CodeGuard Rule
description: The single always-applied Cursor secure-coding rule under .cursor/rules — a credential-hygiene checklist that bans hardcoding secrets, API keys, and tokens in source.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rule

[`.cursor/rules/`](/.cursor/rules/) holds one `codeguard-*.mdc` file today:
`codeguard-1-hardcoded-credentials.mdc`, a secure-coding rule Cursor applies while editing code
in this repository (and, when a plugin ships them, in a target it edits). Its frontmatter
carries `rule_id: codeguard-1-hardcoded-credentials`, a `description`, and `alwaysApply: true`,
so it is considered for every file regardless of language or glob.

The rule states: never store secrets, passwords, API keys, tokens, private keys, certificates,
or connection strings directly in source; treat the codebase as public and untrusted; and
actively scan for recognizable secret formats (AWS keys, Stripe keys, Google API keys, GitHub
tokens, JWTs, PEM key blocks, credentialed connection strings). This page summarizes the rule's
scope; see the file itself for the exact guidance.

An earlier version of this folder held 21 `codeguard-*.mdc` files — two more always-applied
rules (`codeguard-1-crypto-algorithms.mdc`, `codeguard-1-digital-certificates.mdc`) and 18
glob-matched, domain-scoped rules (`codeguard-0-*.mdc`, covering API/web services, auth, authz,
client-side security, cloud/Kubernetes, data storage, DevOps/CI-CD, file handling, framework
guidance, IaC, input validation, logging, mobile, privacy, safe-C functions, session
management, supply chain, and XML/serialization). Those 20 files were removed from the tracked
tree before this wiki's current documented range; no commit in that range or changelog entry
explains the removal, so this page states the current, single-file reality rather than
speculating about why the rest were dropped.

## CodeRabbit's reference audit

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) still audits changed files under both
`references/codeguard/` and `.cursor/rules/` together whenever either changes, checking that
every rule names a concrete replacement for whatever it forbids and that no `rule_id` collides
across files — this check's instructions in `.coderabbit.yaml` are generic over however many
files exist in each folder, so it did not need updating when the 20 files were removed.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists consumed by the harness's own `patch`/`triage` agents
to pick a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
findings. Those are a different artifact from the `.cursor/rules/` file on this page: the
`.cursor/rules/` file is a Cursor-editor rule applied while a human or agent edits code in
*this* repository (or a target repository a plugin ships it into); `references/codeguard/`
is data the sec-overlay harness's own prompts load at investigation/patch time. CodeRabbit's
`codeguard-reference-audit` check is the one place both are cross-checked together for
`rule_id` consistency.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
