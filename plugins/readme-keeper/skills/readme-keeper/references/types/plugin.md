# Claude Code plugin or marketplace README

A Claude Code plugin (a folder with `.claude-plugin/plugin.json`) or a marketplace (a repo with `.claude-plugin/marketplace.json`). This is the first row of the type table, so it wins over every other type. Section order and the manifest-extraction idea adapt `skills/readme/references/patterns/plugin.md` of `rushikeshsakharleofficial/readme-forge` (MIT, Rushikesh Sakharle). This file holds slots only. Fill every slot from a repo file, or omit the section.

A plugin reader asks: what does it add to Claude Code, how do I install it, and what do I type to use it.

## What is a component

Read the plugin folder, not only `plugin.json`. A manifest may list no components. Claude Code finds them by folder.

| Component | Where | README entry |
|---|---|---|
| Skill | `skills/<name>/SKILL.md`. Name and description from its frontmatter | Table row with the skill name and description |
| Command | `commands/<name>.md`. The slash command is `/<plugin>:<name>` | Table row with the command, its argument hint if the file has one, and its description |
| Agent | `agents/<name>.md`. Name and description from frontmatter | Table row |
| Hook | `hooks/hooks.json` or the manifest `hooks` field | One line naming the event and what the hook is for, only if the file says |
| MCP server | `.mcp.json` or the manifest `mcpServers` field | One line per server: name and purpose from the config |

If `plugin.json` does list components, check that each listed path exists. A listed path with no file is a finding.

## Section order, plugin

| # | Section | Slot | Min | Std | Full | Region |
|---|---|---|---|---|---|---|
| 1 | Title and badges | `name` from `plugin.json`. Badges gated by `badges.md`. A version badge reads the manifest `version` | x | x | x | `badges` |
| 2 | Opening | One sentence: what the plugin adds. Source: manifest `description`, the author | x | x | x | |
| 3 | Install | The two commands: add the marketplace, then install the plugin. Fill the marketplace source from the git remote and the names from the manifests | x | x | x | `install` |
| 4 | Usage | One real invocation per main component, from the command or skill files | x | x | x | `quickstart` |
| 5 | Components | Tables of skills, commands, and agents from the folder scan | | x | x | `commands` |
| 6 | Configuration | Settings, env vars, or files the plugin reads, from its scripts and docs | | x | x | `env` |
| 7 | Requirements | Tools the scripts call (a language runtime, a CLI), from script headers and shebangs | | x | x | |
| 8 | Structure | A tree of the plugin folder with one-line purposes | | | x | `structure` |
| 9 | Development | Test and lint commands from the plugin's own docs or scripts | | | x | `commands` |
| 10 | Changelog link | A link to `CHANGELOG.md` if it exists | | | x | |
| 11 | License | The license named by `LICENSE` or the manifest | x | x | x | `license` |

## Section order, marketplace

| # | Section | Slot | Region |
|---|---|---|---|
| 1 | Title and opening | The marketplace `name` and `metadata.description`, or the author's words | `badges` for badges |
| 2 | Add the marketplace | The add command with the repo source | `install` |
| 3 | Plugins | A table from `marketplace.json`: plugin name (linked to its source folder), description, install command | `commands` |
| 4 | Governance or contributing | Only what the repo states: branch rules, release steps, validation command | |
| 5 | Directory guide | One line per top-level folder that has a README | `structure` |
| 6 | License | From `LICENSE` | `license` |

## Depth tiers

- **Minimal:** title, opening, install, one usage line, license.
- **Standard:** adds the components tables, configuration, and requirements.
- **Full:** adds structure, development, and a changelog link.

## Rules

- Install commands use names from the manifests. Never type a plugin or marketplace name by hand.
- Skill, command, and agent names come from file names and frontmatter. A table row for a component with no file is a finding.
- A plugin version shown in the README must equal `plugin.json` `version`. When the version changes, `update` refreshes the `badges` region.
- Only the plugin folder ships on install. Do not tell a reader to run a script outside the plugin folder. Repo-level tooling is for maintainers: say so if documented.
- The maintainer manual (`CLAUDE.md`) never loads for installers. Do not summarize it in the user-facing README.
- Table of contents: add a `toc` region when the README exceeds about 1000 words.

## Facts to read

`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `skills/*/SKILL.md` frontmatter, `commands/*.md`, `agents/*.md`, hooks and MCP config, script shebangs, `CHANGELOG.md`, `LICENSE`, the git remote.
