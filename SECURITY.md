# Security Policy

## Supported versions

Security reports are accepted against the default branch (`main`).

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting:

https://github.com/cjbischoff/cjbischoff-claude-code-tools/security/advisories/new

Do not open a public issue for a security report. Include the affected path,
a short reproduction, and the impact.

## Test fixtures

This repository ships intentionally vulnerable fixtures under
`plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/` for detector tests.
Those strings are not live credentials.
