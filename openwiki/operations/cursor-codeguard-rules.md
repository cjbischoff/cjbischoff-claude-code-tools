---
type: reference
title: Cursor CodeGuard Rules
description: The single always-applied Cursor secure-coding rule under .cursor/rules — hardcoded credentials and secret detection — after this repository consolidated away its prior 21-file, two-family CodeGuard rule set.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rules

[`.cursor/rules/`](/.cursor/rules/) holds secure-coding rules that Cursor applies while editing
code in this repository. Today that is **exactly one file**:

- **`codeguard-1-hardcoded-credentials.mdc`** — `alwaysApply: true`, considered for every file
  regardless of language or glob. Never store secrets, passwords, API keys, tokens, or other
  credentials directly in source; treats the codebase as public and untrusted, and lists
  recognizable secret formats (AWS keys, Stripe keys, GitHub tokens, JWTs, PEM key blocks,
  credentialed connection strings) to actively scan for. Its frontmatter carries a `rule_id`
  matching its filename plus a `description`.

## What changed, and why this page is short on purpose

This repository previously carried 21 `codeguard-*.mdc` files: three always-applied rules
(hardcoded credentials, banned crypto algorithms, digital-certificate checks) plus eighteen
glob-matched files, one per security domain (API/web services, authentication, authorization,
client-side security, cloud/Kubernetes, data storage, DevOps/CI-CD, file handling, framework
guidance, IaC, input validation, logging, mobile, privacy, safe-C, session management,
supply-chain, XML/serialization). That set was consolidated down to the single file above.
Document the current state only — do not reconstruct the deleted families from history, and
do not assume any of their guidance still applies implicitly; if this repository needs that
coverage again, it will reappear as tracked files under `.cursor/rules/` and this page should
be expanded to match.

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) still audits changed files under both
`references/codeguard/` and `.cursor/rules/` together, checking that every rule names a
concrete replacement for whatever it forbids and that no `rule_id` collides across files — that
check's scope did not shrink even though the `.cursor/rules/` side of it now has one file
instead of twenty-one.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
domain-scoped markdown checklists consumed by the harness's own `patch`/`triage` agents to pick
a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
findings. Those are a different artifact from the `.cursor/rules/` file on this page: the
`.cursor/rules/` file is a Cursor-editor rule applied while a human or agent edits code in
*this* repository; `references/codeguard/` is data the sec-overlay harness's own prompts load
at investigation/patch time. CodeRabbit's `codeguard-reference-audit` check is the one place
both are cross-checked together for `rule_id` consistency.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy, unaffected by this consolidation.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
