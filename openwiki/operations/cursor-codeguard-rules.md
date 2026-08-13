---
type: reference
title: Cursor CodeGuard Rules
description: The two families of secure-coding rules under .cursor/rules — three always-applied rules for banned crypto, hardcoded credentials, and certificate checks, and eighteen glob-matched rules for specific security domains.
tags: [operations, cursor-rules, codeguard, secure-coding]
---

# Cursor CodeGuard rules

[`.cursor/rules/`](/.cursor/rules/) holds 21 `codeguard-*.mdc` files: secure-coding rules that
Cursor applies while editing code in this repository (and, when a plugin ships them, in a
target it edits). Each file's frontmatter carries a `rule_id` matching its filename, a
`description`, and either `globs` (which files it matches) or `alwaysApply: true`. This page
summarizes the two families by topic; it does not reproduce rule bodies — see the file itself
for the exact guidance.

## Always-applied rules (`codeguard-1-*`)

Three files carry `alwaysApply: true`, meaning they are considered for every file regardless of
language or glob:

- **`codeguard-1-hardcoded-credentials.mdc`** — never store secrets, passwords, API keys,
  tokens, or other credentials directly in source; treats the codebase as public and untrusted,
  and lists recognizable secret formats (AWS keys, Stripe keys, GitHub tokens, JWTs, PEM key
  blocks, credentialed connection strings) to actively scan for.
- **`codeguard-1-crypto-algorithms.mdc`** — bans specific weak cryptographic algorithms/modes
  outright (the always-applied counterpart to the machine-checked
  [`approved-crypto-algorithms.yaml`](../plugins/sec-overlay/references.md#machine-checked-policy-and-schemas)
  the sec-overlay harness itself uses — the two are independent but philosophically aligned).
- **`codeguard-1-digital-certificates.mdc`** — requires parsing and validating any X.509
  certificate data encountered (PEM strings, `.pem`/`.crt`/`.cer`/`.der` file reads, certificate
  library calls) against mandatory checks including expiration status.

These three are the highest-priority family: CodeRabbit's `codeguard-reference-audit`
finishing-touch (see [code review](../governance/code-review.md)) audits changed files under
both `references/codeguard/` and `.cursor/rules/` together, checking that every rule names a
concrete replacement for whatever it forbids and that no `rule_id` collides across files.

## Glob-matched rules (`codeguard-0-*`)

Eighteen files match language-specific globs (e.g. `**/*.py,**/*.js,**/*.ts,...`) rather than
applying unconditionally, one per security domain:

| Domain | File |
|---|---|
| Additional cryptography & TLS | `codeguard-0-additional-cryptography.mdc` |
| API and web services | `codeguard-0-api-web-services.mdc` |
| Authentication and MFA | `codeguard-0-authentication-mfa.mdc` |
| Authorization and access control | `codeguard-0-authorization-access-control.mdc` |
| Client-side web security | `codeguard-0-client-side-web-security.mdc` |
| Cloud orchestration / Kubernetes | `codeguard-0-cloud-orchestration-kubernetes.mdc` |
| Data storage | `codeguard-0-data-storage.mdc` |
| DevOps CI/CD and containers | `codeguard-0-devops-ci-cd-containers.mdc` |
| File handling and uploads | `codeguard-0-file-handling-and-uploads.mdc` |
| Framework and language guidance | `codeguard-0-framework-and-languages.mdc` |
| Infrastructure-as-code security | `codeguard-0-iac-security.mdc` |
| Input validation and injection | `codeguard-0-input-validation-injection.mdc` |
| Logging | `codeguard-0-logging.mdc` |
| Mobile apps | `codeguard-0-mobile-apps.mdc` |
| Privacy and data protection | `codeguard-0-privacy-data-protection.mdc` |
| Safe C functions | `codeguard-0-safe-c-functions.mdc` |
| Session management and cookies | `codeguard-0-session-management-and-cookies.mdc` |
| Supply-chain security | `codeguard-0-supply-chain-security.mdc` |
| XML and serialization | `codeguard-0-xml-and-serialization.mdc` |

For example, `codeguard-0-additional-cryptography.mdc` matches source files across C, Go, Java,
JavaScript/TypeScript, Kotlin, PHP, Python, Ruby, Swift, and config formats (YAML/XML/XSD),
and covers algorithm/mode choice, key management (HSM/KMS, key separation, rotation), data-at-rest
encryption, and TLS configuration — guidance that complements, rather than duplicates, the
always-applied `codeguard-1-crypto-algorithms.mdc` above.

## How this differs from `references/codeguard/`

The sec-overlay plugin ships its own, separate `codeguard/` checklists under
[`references/`](../plugins/sec-overlay/references.md#codeguard--secure-coding-checklists-for-fixing) —
seven domain-scoped markdown checklists consumed by the harness's own `patch`/`triage` agents
to pick a correct remediation shape, and by `citations.py` to stamp advisory CodeGuard ids onto
findings. Those are a different artifact from the `.cursor/rules/` files on this page: the
`.cursor/rules/` files are Cursor-editor rules applied while a human or agent edits code in
*this* repository (or a target repository a plugin ships them into); `references/codeguard/`
is data the sec-overlay harness's own prompts load at investigation/patch time. CodeRabbit's
`codeguard-reference-audit` check is the one place both are cross-checked together for
`rule_id` consistency.

## Related pages

- [sec-overlay references](../plugins/sec-overlay/references.md) — the harness's own
  `codeguard/` checklists and machine-checked crypto policy.
- [Code review](../governance/code-review.md) — the `codeguard-reference-audit` finishing-touch
  that inspects both rule sets.
