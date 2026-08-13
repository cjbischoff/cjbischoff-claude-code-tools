---
type: Repository guide
title: Repository Wiki Instructions
description: Brief for init and update runs of the cjbischoff-claude-code-tools marketplace wiki.
tags: [documentation, repository, code-wiki, marketplace, plugins]
---

# OpenWiki brief — Claude Code plugin marketplace

This file is the wiki brief. OpenWiki reads it on `--init` and `--update` and
does not rewrite it during normal runs. Keep it accurate; do not paste generated
pages back into it.

## What this repository is

This is not an application server. It is a **Claude Code plugin marketplace**
that distributes personal plugins for Christopher Bischoff. There is no
production runtime, no HTTP API, and no database. The shipping unit is a plugin
directory under `plugins/`.

Document it as a distribution and governance system plus the plugins it
ships, not as a web app.

## Audience

Rank these in order when a trade-off appears:

1. A coding agent that must install a plugin, change this repo without
   breaking governance, or run sec-overlay against a target.
2. A human cloning the marketplace who has not read `README.md`.

## Success test

An agent that reads only the wiki must be able to:

1. Add this marketplace and install `sec-overlay`.
2. Make a functionality change on a branch that would pass the pre-commit
   hooks (README, CHANGELOG, folder README, plugin version bump).
3. Explain the sec-overlay pipeline: deterministic core vs LLM agents,
   tool-receipt confirmation, producer vs adversary, and what a run emits.

If any of those answers is reachable only by reading source, the wiki is
incomplete.

## Priorities, highest first

1. **Marketplace contract.** `.claude-plugin/marketplace.json`, one plugin
   per `plugins/<name>/`, `.claude-plugin/plugin.json`,
   `claude plugin validate .`. How install paths resolve from
   `${CLAUDE_PLUGIN_ROOT}`. Scripts must not escape the plugin directory.
2. **Commit governance.** Branch naming, Conventional Commits, the prek
   hooks in `scripts/hooks/`, the Directory Guide rule, the shipping-file
   semver bump, and the GitHub ruleset on `main`. Cite the hook that
   enforces each rule.
3. **sec-overlay architecture.** Skill playbook (`SKILL.md`), Python core
   (`helpers/sec_overlay`), agent prompts (`agents/`), references
   (`references/`). The four principles, the phase order, the tool-receipt
   gate, phase-adversary gates, and the workspace artifact layout.
4. **How to run sec-overlay.** Deterministic `cli scan` smoke path vs full
   agentic audit. Preflight, env-only test failures, and the
   do-not-execute-the-target invariant.
5. **Repo security automation.** Dependency review, Dependabot, CodeQL
   default setup, secret scanning, SHA-pinned Actions, read-only default
   workflow token, CodeRabbit config. Describe what each control does;
   do not copy YAML.
6. **Cursor CodeGuard rules** under `.cursor/rules/`. Summarize the
   families (banned crypto, no hardcoded credentials, certificate checks).
   Do not reproduce every rule body.

## Required structure

Use directories, not one page per topic area:

- `marketplace/` — manifest, plugin layout, install, validate, versioning.
- `governance/` — hooks, commit rules, Directory Guide, GitHub ruleset,
  CodeRabbit.
- `plugins/sec-overlay/` — overview, pipeline, agents, helpers, references,
  running an audit, developing the skill.
- `operations/` — GitHub security features, Actions hardening, OpenWiki
  refresh.

Do not merge all agents onto one page. Give the pipeline its own page with
a Mermaid flowchart grounded in `SKILL.md` and `agents/README.md`.

## Source precedence

When two sources disagree, prefer in this order:

1. Hook scripts and `plugin.json` / `marketplace.json` — machine-enforced.
2. Root `CLAUDE.md` and `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md`.
3. `SKILL.md` and folder `README.md` files.
4. Root `README.md` and `CHANGELOG.md`.
5. Historical specs under `docs/superpowers/` — use for why a change
   landed; never let a dated plan override current code.

Verify counts against the filesystem (plugins, agents, hook scripts, test
files), not against prose. Root `README.md` Status section lags; the
helpers tests and `plugin.json` version are authoritative.

## Ground every page

Cite the file that proves each claim. Prefer stable paths and symbol names
over line numbers. For each hook, name the test script that proves it.
For each sec-overlay invariant (tool-receipt gate, phase adversary,
stdlib-only core), cite the module that enforces it.

## Diagrams

Add Mermaid diagrams for:

- Marketplace → plugin → skill → helpers/agents/references.
- sec-overlay producer vs adversary flow (reuse the structure in
  `plugins/sec-overlay/skills/sec-overlay/agents/README.md`).
- The audit phase order from `SKILL.md` / skill `CLAUDE.md`.

Ground every diagram in inspected source. Do not invent phases.

## Out of scope

Do not document seeded vulnerable fixtures as if they were production
architecture. Paths under `.openwikiignore` are excluded deliberately.
Mention that fixtures exist for detector tests; do not walk their source.

Do not document individual dogfooding runs, GSD notes, or local scan
output. Do not copy `prompt-constants.md` or ASVS JSON verbatim; name the
file and what consumes it.

Do not document OpenWiki's own internals beyond how this repo runs it
(brief, ignore file, CI, no telemetry).
