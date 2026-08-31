---
type: reference
title: Cursor CodeGuard Rules
description: The single always-applied Cursor secure-coding rule under .cursor/rules — banning hardcoded credentials — and how it differs from the sec-overlay plugin's own references/codeguard/ checklists.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rules

[`.cursor/rules/`](/.cursor/rules/) holds one `codeguard-*.mdc` file:
**`codeguard-1-hardcoded-credentials.mdc`** — a secure-coding rule that Cursor applies while
editing code in this repository. Its frontmatter carries `rule_id: codeguard-1-hardcoded-credentials`,
a `description`, and `alwaysApply: true`, so it is considered for every file regardless of
language. It states: never store secrets, passwords, API keys, tokens, or other credentials
directly in source; treat the codebase as public and untrusted; and it lists recognizable
secret formats (AWS keys, Stripe keys, GitHub tokens, JWTs, PEM key blocks, credentialed
connection strings) to actively scan for.

This is a smaller surface than earlier in this repository's history, when `.cursor/rules/`
held twenty-one files across an "always-applied" family (hardcoded credentials, banned crypto
algorithms, certificate validation) and an eighteen-file, glob-matched family covering
individual security domains (authentication, injection, IaC, supply chain, and so on). Only
the hardcoded-credentials rule remains tracked; if you are looking for the crypto-algorithm or
certificate rules, or any of the domain-specific glob-matched rules, they are gone from this
repository — do not assume they still apply. Verify what exists with `ls .cursor/rules/`
before writing guidance that depends on a specific rule file.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists consumed by the harness's own `patch`/triage agents to
pick a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
findings. Those are a different artifact from the one `.cursor/rules/` file on this page: the
`.cursor/rules/` file is a Cursor-editor rule applied while a human or agent edits code in
*this* repository; `references/codeguard/` is data the sec-overlay harness's own prompts load
at investigation/patch time. The machine-checked
[`approved-crypto-algorithms.yaml`](../plugins/sec-overlay/references.md#machine-checked-policy-and-schemas)
policy the harness enforces in code is philosophically aligned with — but operationally
independent of — the hardcoded-credentials rule on this page; the two systems do not share
configuration.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy.
- [Code review](../governance/code-review.md) — CodeRabbit's review configuration, which is
  independent of this Cursor rule.
