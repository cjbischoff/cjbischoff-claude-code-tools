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

A full audit now checks its own output before handing it off: a deterministic `artifact-gate`
followed by an opus `artifact-review` adversary run after `report`, catching a stale or
overclaiming report before a human reads it.

The architecture and threat-model phases produce standards-based artifact trees (C4 + arc42,
STRIDE + a derived data-flow diagram), each checked by a deterministic gate before the pipeline
continues.

A code-derived route census (`route_census.py`) now reads route registrations straight from
source, instead of only from recon's own output.

Every agent prompt imports the same sixteen verbatim rule blocks from
`references/prompt-constants.md`, so core rules never drift between prompts.

A dependency-sink catalog (`dependency_sinks.py`) names dependencies whose own code holds the
sink. Run it directly with `python -m sec_overlay.dependency_sinks match --root <dir>`.

The skill's documented phase order is generated, not hand-maintained. `phase_docs.py` renders it
from `PHASE_TABLE` into every document that states it. Run
`python -m sec_overlay.phase_docs --check` to fail on a stale document, or `--write` to regenerate
each one in place.

The dev benchmark ships a committed seed corpus (`skills/sec-overlay/helpers/bench/corpus_seed/`,
public entries only), and `.github/workflows/sec-overlay-tests.yml` gates every pull request on
the two `locked` fixtures staying detected by a deterministic scan.

The composite [`action.yml`](action.yml) runs review mode on a pull request, uploads the SARIF to
code scanning, and posts findings as a pull-request review — critical and high inline, the rest in
the summary. The review event is `COMMENT`, so it never blocks a merge on its own. The poster is a
stdlib Python script (`sec_overlay.pr_poster`), no Node dependency.

## More

| To understand… | Read |
|-----------------|------|
| What changed between releases | [`CHANGELOG.md`](CHANGELOG.md) |
| The skill in depth (architecture, worked example, output workspace) | [`skills/sec-overlay/README.md`](skills/sec-overlay/README.md) |
| The full phase-by-phase operating playbook | [`skills/sec-overlay/SKILL.md`](skills/sec-overlay/SKILL.md) |
| How to develop the skill, including the vendored (not submoduled) semgrep ruleset | [`CLAUDE.md`](CLAUDE.md) |
