---
type: reference
title: Cursor CodeGuard Rules
description: The single always-applied Cursor secure-coding rule remaining under .cursor/rules/ (hardcoded credentials), why the other twenty domain-scoped CodeGuard rules were dropped, and how CodeRabbit's codeguard-reference-audit check still cross-references this folder against references/codeguard/.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rules

[`.cursor/rules/`](/.cursor/rules/) holds secure-coding rules that Cursor applies while editing
code in this repository. It is down to **one file**,
[`codeguard-1-hardcoded-credentials.mdc`](/.cursor/rules/codeguard-1-hardcoded-credentials.mdc):
twenty other `codeguard-*.mdc` files — eighteen glob-matched domain checklists plus two other
always-applied rules (banned crypto algorithms, digital-certificate validation) — were removed.
CHANGELOG.md records why: "Drop 21 unused CodeGuard Cursor rules so editor context keeps only
the always-on hardcoded-credentials rule." The root README's Artifact inventory table now lists
only this one file under `.cursor/rules/`.

## The remaining rule

`codeguard-1-hardcoded-credentials.mdc` carries `alwaysApply: true` and `rule_id:
codeguard-1-hardcoded-credentials` in its frontmatter — it is considered for every file
regardless of language or glob. It instructs: never store secrets, passwords, API keys, tokens,
or other credentials directly in source; treat the codebase as public and untrusted; and lists
recognizable secret formats to actively scan for (AWS keys, Stripe keys, Google API keys, GitHub
tokens, JWTs, PEM key blocks, credentialed connection strings).

## Why "unused," and what still exists

The removed rules were dropped as unused editor context, not because the underlying security
guidance stopped mattering. The sec-overlay plugin's own, separate `codeguard/` checklists under
[`references/codeguard/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing)
still cover the same domains (input validation/injection, cryptography, authorization,
client-side, file handling, API/web services, safe-C functions) — those are consumed by the
harness's own `patch`/`triage` agents and by `citations.py`, independent of this repository's
editor rules. The machine-checked
[`approved-crypto-algorithms.yaml`](../plugins/sec-overlay/references.md#machine-checked-policy-and-schemas)
the sec-overlay harness uses for its own crypto findings is likewise unaffected by this removal.

## CodeRabbit's `codeguard-reference-audit` still watches this folder

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) still audits changed files under both
`references/codeguard/` and `.cursor/rules/` together, checking that every rule names a concrete
replacement for whatever it forbids and that no `rule_id` collides across files — its
instructions were not narrowed when the twenty files were dropped, so it now simply has one
`.cursor/rules/` file to check instead of twenty-one. Add a new `.cursor/rules/codeguard-*.mdc`
file here only if it is genuinely used going forward; this check will flag a `rule_id` collision
or a missing replacement on whatever file(s) exist at review time.

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
