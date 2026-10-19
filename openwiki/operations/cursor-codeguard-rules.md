---
type: reference
title: Cursor CodeGuard Rules
description: The single always-applied secure-coding rule remaining under .cursor/rules — a ban on hardcoded credentials — after the glob-matched domain rules and the crypto/certificate always-on rules were removed from this repository.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rules

[`.cursor/rules/`](/.cursor/rules/) holds secure-coding rules that Cursor applies while editing
code in this repository. As of this writing it holds exactly **one** file:
`codeguard-1-hardcoded-credentials.mdc`. The earlier, larger rule set — three always-applied
rules (crypto algorithms, digital certificates, hardcoded credentials) plus eighteen
glob-matched domain rules (`codeguard-0-*.mdc`, covering API/web services, authn/authz,
client-side security, cloud/Kubernetes, data storage, DevOps/CI/CD, file handling,
framework/language guidance, IaC, input validation, logging, mobile, privacy, safe-C,
session management, and supply-chain) — was removed from `.cursor/rules/` in this repository's
history. Only the hardcoded-credentials rule survives.

## The remaining rule

`codeguard-1-hardcoded-credentials.mdc` carries `alwaysApply: true` (`globs: **/*`), so it is
considered for every file regardless of language. It forbids storing secrets, passwords, API
keys, tokens, or other credentials directly in source; treats the codebase as public and
untrusted; and lists recognizable secret formats to actively scan for (AWS access keys, Stripe
keys, Google API keys, GitHub tokens, JWTs, PEM private-key blocks, credentialed connection
strings). Its frontmatter carries a `rule_id` (`codeguard-1-hardcoded-credentials`) matching its
filename, a `description`, and a `version`.

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) still audits changed files under both
`references/codeguard/` and `.cursor/rules/` together, checking that every surviving rule names
a concrete replacement for whatever it forbids and that no `rule_id` collides across files —
that check now has one `.cursor/rules/` file to reconcile against instead of twenty-one.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
domain-scoped markdown checklists consumed by the harness's own `patch`/triage agents to pick a
correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto findings.
Those are a different artifact from the `.cursor/rules/` file on this page: `.cursor/rules/`
applies while a human or agent edits code in *this* repository; `references/codeguard/` is data
the sec-overlay harness's own prompts load at investigation/patch time. CodeRabbit's
`codeguard-reference-audit` check is the one place both are cross-checked together for
`rule_id` consistency.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy, which remain in place even though
  the repo-wide Cursor rule set was reduced.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
