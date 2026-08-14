# sec-overlay

A self-contained, **agentic security-audit harness**. Point it at a codebase and it finds
*actually-exploitable* vulnerabilities, then hands a security engineer artifacts they can act
on: a threat model, per-finding evidence, a SARIF file, a Markdown report, and a manual
runtime-test plan.

The core idea in one sentence: **run cheap mechanical tools to find candidates, use LLM
agents to investigate whether each candidate is real, and never let an LLM's opinion alone
confirm a finding — a mechanical tool receipt is always required.**

## Install

```text
/plugin marketplace add cjbischoff/cjbischoff-claude-code-tools
/plugin install sec-overlay@cjbischoff-claude-code-tools
```

## Prerequisites

- `semgrep`, `codeql` (with the language query packs you need), `ast-grep`, `osv-scanner` on `PATH`
- `uv`, to run the Python core
- A semgrep ruleset — the plugin ships only a minimal smoke ruleset; supply your own for full coverage

## Quick start

Fastest way to see output — a deterministic smoke scan, no agents:

```bash
cd skills/sec-overlay/helpers
uv run python -m sec_overlay.cli scan \
  --target <path-to-code> \
  --config rules/smoke.yaml \
  --sha "$(git -C <path-to-code> rev-parse HEAD)"
# workspace defaults to <target>/.sec-overlay/<slug>/
```

(For an installed plugin, the helpers live at `${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/helpers`.)

This runs semgrep → normalize → SARIF/Markdown only. It is the smoke path, **not** a real
audit (no agents, no gate ladder). For a full agentic audit, see the skill playbook below.

## More

| To understand… | Read |
|-----------------|------|
| What changed between releases | [`CHANGELOG.md`](CHANGELOG.md) |
| The skill in depth (architecture, worked example, output workspace) | [`skills/sec-overlay/README.md`](skills/sec-overlay/README.md) |
| The full phase-by-phase operating playbook | [`skills/sec-overlay/SKILL.md`](skills/sec-overlay/SKILL.md) |
