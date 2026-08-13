---
type: architecture-overview
title: Marketplace Manifest and Plugin Layout
description: How the cjbischoff-claude-code-tools repository is structured as a Claude Code plugin marketplace, and how the marketplace and plugin manifests, install path, and plugin directory boundary work together.
tags: [marketplace, claude-plugin, manifest, plugin-layout]
---

# Marketplace manifest and plugin layout

This repository is a **Claude Code plugin marketplace**: a distribution point for personal
Claude Code plugins, not an application with a runtime, HTTP API, or database. The unit that
Claude Code installs is a **plugin directory** under [`plugins/`](../../plugins/README.md) — for
this repository, that is a single plugin, `sec-overlay` (see
[sec-overlay overview](../plugins/sec-overlay/overview.md)).

## The marketplace manifest

`.claude-plugin/marketplace.json` is the machine-read root of the marketplace. It declares:

- `name` — the marketplace id, `cjbischoff-claude-code-tools`, matching the repo name.
- `owner.name` — the marketplace owner (`Christopher Bischoff`).
- `metadata.description` — a one-line description shown to a user browsing marketplaces.
- `plugins` — an array with one entry per distributed plugin. Each entry has:
  - `name` — must equal the plugin directory name under `plugins/` and the plugin's own
    `name` field in its `plugin.json` (`plugins/README.md`'s naming convention).
  - `source` — a relative path to the plugin directory, e.g. `./plugins/sec-overlay`.
  - `description` — shown alongside the plugin in marketplace listings.

Today the array has exactly one entry, `sec-overlay`, sourced from `./plugins/sec-overlay`.
Adding a second plugin means adding both a new `plugins/<name>/` directory and a matching
entry here — CodeRabbit's `**/.claude-plugin/*.json` path instruction (see
[code review](../governance/code-review.md)) checks that every plugin directory has a
marketplace entry.

## Installing from this marketplace

```
/plugin marketplace add cjbischoff/cjbischoff-claude-code-tools
/plugin install sec-overlay@cjbischoff-claude-code-tools
```

The first command registers this repository as a marketplace source (Claude Code reads
`.claude-plugin/marketplace.json`); the second installs the named plugin from it. This is the
literal install path documented in the root [`README.md`](/README.md).

## Plugin directory layout and the plugin manifest

Each plugin lives entirely under `plugins/<name>/` (`plugins/README.md`'s Directory Guide
entry: "one directory per distributed plugin"). For `sec-overlay`:

```
plugins/sec-overlay/
  .claude-plugin/plugin.json      # plugin manifest
  skills/sec-overlay/             # the skill Claude Code discovers and loads
    SKILL.md
    CLAUDE.md
    README.md
    agents/
    helpers/
    references/
```

`plugins/sec-overlay/.claude-plugin/plugin.json` is the **plugin manifest**:

```json
{
  "name": "sec-overlay",
  "description": "Agentic security-audit harness: runs SAST, investigates candidates with multi-agent gates, and emits SARIF + Markdown reports.",
  "version": "0.2.0",
  "author": { "name": "Christopher Bischoff" }
}
```

- `name` must match the marketplace entry's `name` and the plugin's own directory name.
- `version` is a plain semver string. It is bumped automatically on shipping-file changes — see
  [validation and versioning](validation-and-versioning.md) for the exact rule and where it is
  (and is not) enforced.
- The manifest declares **no `components` field**. Per the root README's Decisions section,
  this is intentional: Claude Code's default behavior is to scan the plugin's `skills/`
  directory for skills automatically ("the default `skills/` directory scan handles
  discovery, strict mode stays at its default (`true`)"). There is nothing else to wire up —
  every subdirectory under `skills/` that contains a `SKILL.md` is a discoverable skill.

## `${CLAUDE_PLUGIN_ROOT}` and the plugin-directory boundary

When Claude Code installs a plugin, **only that plugin's own directory is copied to the
plugin cache** — nothing else in the marketplace repository ships with it. This has two
concrete consequences documented in the root [`CLAUDE.md`](/CLAUDE.md) Conventions section:

1. **Paths must resolve from `${CLAUDE_PLUGIN_ROOT}`, never from the marketplace repo root.**
   The sec-overlay skill's own instructions consistently use this pattern, e.g. running the
   deterministic scan from
   `${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/helpers` (see
   [running an audit](../plugins/sec-overlay/running-an-audit.md)). A path like
   `../../scripts/hooks/...` or an absolute `/Users/...` path inside a plugin file would work
   in this repository's checkout but break the moment the plugin is installed standalone.
2. **Scripts must not reference paths outside their plugin directory.** The root `CLAUDE.md`
   states this as a hard convention: "Scripts must not reference paths outside their plugin
   directory." CodeRabbit's `no-paths-outside-plugin` pre-merge check (see
   [code review](../governance/code-review.md)) enforces this in review: it fails on a
   parent-relative path that escapes the plugin root, an absolute path under `/Users`, `/home`,
   or `/tmp`, or a reference to a sibling top-level directory such as `scripts/` or `docs/`.

Put together: everything a plugin needs at runtime — its skill definition, agent prompts,
Python helpers, and reference data — must live inside `plugins/<name>/`, and every reference
to those files inside the plugin's own instructions must be relative to the plugin root (or to
`${CLAUDE_PLUGIN_ROOT}` once installed), never to the surrounding marketplace repository.

## Related pages

- [Validation and versioning](validation-and-versioning.md) — `claude plugin validate .` and
  the automatic semver bump rule.
- [sec-overlay overview](../plugins/sec-overlay/overview.md) — what the one shipped plugin does.
- [Commit governance](../governance/hooks-and-commits.md) — the hooks that gate any change to
  this repository, including plugin files.
