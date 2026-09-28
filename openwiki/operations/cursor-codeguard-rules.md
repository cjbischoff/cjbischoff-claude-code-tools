---
type: reference
title: Cursor CodeGuard Rule
description: The single always-on Cursor secure-coding rule under .cursor/rules — banning hardcoded credentials — and why the eighteen glob-matched and two other always-applied rules that used to live alongside it were removed.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rule

[`.cursor/rules/`](/.cursor/rules/codeguard-1-hardcoded-credentials.mdc) holds exactly **one**
file today: `codeguard-1-hardcoded-credentials.mdc`, an always-applied Cursor rule (its
frontmatter carries `alwaysApply: true`) that forbids storing secrets, passwords, API keys,
tokens, or other credentials directly in source — it treats the codebase as public and
untrusted, and lists recognizable secret formats (AWS keys, Stripe keys, GitHub tokens, JWTs,
PEM key blocks, credentialed connection strings) to actively scan for. This is the one Cursor
rule the root README's Directory Guide tracks (`.cursor/rules/codeguard-1-hardcoded-credentials.mdc`).

## What used to be here

Twenty other `codeguard-*.mdc` files — two more always-applied rules
(`codeguard-1-crypto-algorithms.mdc`, banning weak crypto algorithms/modes;
`codeguard-1-digital-certificates.mdc`, requiring X.509 certificate validation) and eighteen
glob-matched, domain-scoped rules (API/web services, authentication, authorization, client-side
security, cloud/Kubernetes, data storage, DevOps/CI-CD, file handling, framework guidance,
IaC security, input validation, logging, mobile apps, privacy, safe C functions, session
management, supply-chain security, XML/serialization) — were dropped in the same range this
wiki now documents. The root `CHANGELOG.md` records the change plainly: "Drop 21 unused
CodeGuard Cursor rules so editor context keeps only the always-on hardcoded-credentials rule."
They are not referenced anywhere else in this repository; treat their prior families
(always-applied vs. glob-matched) as historical structure, not current guidance.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists consumed by the harness's own `patch`/`triage` agents
to pick a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
findings. Those are a different artifact from the `.cursor/rules/` file on this page: the
`.cursor/rules/` rule is a Cursor-editor rule applied while a human or agent edits code in
*this* repository (or a target repository a plugin ships it into); `references/codeguard/` is
data the sec-overlay harness's own prompts load at investigation/patch time. CodeRabbit's
`codeguard-reference-audit` finishing-touch (see [code review](../governance/code-review.md))
is the one place both are still cross-checked together for `rule_id` consistency — its
instructions still name both `references/codeguard/` and `.cursor/rules/` even though the
latter is now a single file, so a newly added Cursor rule (or a new `references/codeguard/`
checklist) is still audited for a matching `rule_id`/filename and a named replacement for
anything it bans.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
