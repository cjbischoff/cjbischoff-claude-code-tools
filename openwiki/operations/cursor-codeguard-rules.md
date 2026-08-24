---
type: reference
title: Cursor CodeGuard Rules
description: The single always-applied secure-coding rule remaining under .cursor/rules — banning hardcoded credentials — after the eighteen glob-matched domain rules and the two other always-applied rules were removed from this repository.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rules

[`.cursor/rules/`](/.cursor/rules/) now holds exactly **one** `codeguard-*.mdc` file:
`codeguard-1-hardcoded-credentials.mdc`. Earlier revisions of this repository shipped 21 such
files (three always-applied `codeguard-1-*` rules plus eighteen glob-matched `codeguard-0-*`
domain rules); the eighteen domain rules and the other two always-applied rules
(`codeguard-1-crypto-algorithms.mdc`, `codeguard-1-digital-certificates.mdc`) were deleted from
the tree. This page documents what remains — do not assume the wider family still exists.

## `codeguard-1-hardcoded-credentials.mdc`

Frontmatter carries `rule_id: codeguard-1-hardcoded-credentials`, `alwaysApply: true` (applies
to every file Cursor edits, regardless of language), and `globs: **/*`. The body:

- Never store secrets, passwords, API keys, tokens, private keys, certificates, signing keys,
  credentialed connection strings, or OAuth/webhook secrets directly in source code — treat the
  codebase as public and untrusted.
- Names recognizable secret formats to actively scan for: AWS key prefixes (`AKIA`, `ASIA`, …),
  Stripe (`sk_live_`, `pk_test_`, …), Google API keys (`AIza…`), GitHub tokens (`ghp_`, `gho_`,
  …), JWTs (`eyJ…`), PEM private-key blocks, and credentialed connection-string URLs.
- Flags warning signs even without a recognizable prefix: variable names containing
  `password`/`secret`/`key`/`token`/`auth`, long random-looking strings, and base64 blobs near
  authentication code.
- Requires explaining how and why the rule was applied whenever it fires.

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) audits this file alongside `references/codeguard/`
— it checks that every rule file's `rule_id` matches its filename and that no `rule_id`
collides across the two directories, regardless of how many files exist on either side.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists consumed by the harness's own `patch`/`triage` agents
to pick a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
findings. Those are a different artifact from the `.cursor/rules/` file on this page: the
`.cursor/rules/` file is a Cursor-editor rule applied while a human or agent edits code in
*this* repository; `references/codeguard/` is data the sec-overlay harness's own prompts load
at investigation/patch time. CodeRabbit's `codeguard-reference-audit` check is the one place
both are cross-checked together for `rule_id` consistency.

## Adding a rule back

If you add a new `.cursor/rules/codeguard-*.mdc` file, give it a `rule_id` matching its
filename, state whether the pattern it bans is prohibited or merely deprecated, and name a
concrete replacement for every construct it forbids — `codeguard-reference-audit` flags a rule
that bans a primitive with no offered replacement, and any `rule_id` collision with
`references/codeguard/` or another `.cursor/rules/` file.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
