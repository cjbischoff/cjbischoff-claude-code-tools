---
type: reference
title: Cursor CodeGuard Rule
description: The one always-applied Cursor rule remaining under .cursor/rules — banning hardcoded credentials — after the repository consolidated its eighteen glob-matched secure-coding rules and two other always-applied rules out of .cursor/rules, distinct from the sec-overlay plugin's own references/codeguard/ checklists.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rule

[`.cursor/rules/`](/.cursor/rules/) now holds exactly **one** file:
[`codeguard-1-hardcoded-credentials.mdc`](/.cursor/rules/codeguard-1-hardcoded-credentials.mdc).
This is a large reduction from an earlier 21-file `codeguard-*.mdc` family (three
always-applied rules plus eighteen glob-matched, domain-scoped rules) — the eighteen
glob-matched files and two of the three always-applied files (`codeguard-1-crypto-algorithms.mdc`,
`codeguard-1-digital-certificates.mdc`) were deleted from this repository's own Cursor
configuration. The root README's Artifact inventory table now lists only the one remaining
file, confirming this is the current, intended shape rather than an in-progress deletion.

## The remaining rule

- **`codeguard-1-hardcoded-credentials.mdc`** — `alwaysApply: true`; never store secrets,
  passwords, API keys, tokens, or other credentials directly in source. Treats the codebase as
  public and untrusted, and lists recognizable secret formats (AWS keys, Stripe keys, GitHub
  tokens, JWTs, PEM key blocks, credentialed connection strings) to actively scan for. Its
  frontmatter carries a `rule_id` matching its filename and a `description`, per the same shape
  every file in this family used.

CodeRabbit's `codeguard-reference-audit` finishing-touch (see
[code review](../governance/code-review.md)) still audits changed files under both
`references/codeguard/` and `.cursor/rules/` together, checking that every rule names a
concrete replacement for whatever it forbids and that no `rule_id` collides across files — that
check's instructions were not narrowed when the eighteen glob-matched files were removed, so it
now simply has one file to check on the `.cursor/rules/` side instead of twenty-one.

## Why this differs from `references/codeguard/` — and why it still exists separately

The sec-overlay plugin ships its own, unrelated `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists, unchanged in this consolidation, consumed
programmatically by the harness's own `codeguard.py` loader and the patch/triage agents to pick
a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
findings. These are a different artifact from the one `.cursor/rules/` file on this page: the
`.cursor/rules/` file is a Cursor-editor rule applied while a human or agent edits code in
*this* repository (or a target repository a plugin ships it into); `references/codeguard/` is
data the sec-overlay harness's own prompts load at investigation/patch time, and never edits
code directly. The domain coverage the eighteen deleted glob-matched Cursor rules once provided
(API/web, authn/authz, client-side, crypto, file-handling, injection, IaC, mobile, logging,
etc.) is not the same seven domains as `references/codeguard/`, and the deletion did not add
those domains there — this repository's own edit-time secure-coding guidance is narrower now
than it was, while the harness's fix-time checklists are unchanged.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own,
  unrelated `codeguard/` checklists and machine-checked crypto policy.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets together.
