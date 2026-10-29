# CLI README

A tool run as a command in a terminal. Signals: `bin` in `package.json`, `[project.scripts]` in `pyproject.toml`, `[[bin]]` in `Cargo.toml`, or a `cmd/` folder in a Go module. Adapted from the CLI skeleton of the readme skill (Christopher Bischoff) and the CLI section order in `povvo/claudikins-github-readme-for-perfectionists` (MIT, Ethan Lee). This file holds slots only. Fill every slot from a repo file, or omit the section.

The main friction for a CLI reader is installation and the first command. Put both near the top.

## Section order

| # | Section | Slot | Min | Std | Full | Region |
|---|---|---|---|---|---|---|
| 1 | Title and badges | `{tool name}` from the manifest. Badges gated by `badges.md` | x | x | x | `badges` |
| 2 | Opening | One sentence: what the tool does. Then: who needs it, or what it replaces, if the repo or author says | x | x | x | |
| 3 | Demo | A screenshot, GIF, or sample terminal session that exists in the repo. Ask for one if none exists. Never invent output | | x | x | |
| 4 | Install | The command that produces the executable, per the lockfile or manifest. Several methods only when the repo shows them (a release workflow, a formula, a Dockerfile) | x | x | x | `install` |
| 5 | Usage | The real subcommand and flag names, read from the CLI definition in source | x | x | x | `commands` |
| 6 | Options | Only the flags worth calling out. Point to the tool's help output for the rest | | x | x | `commands` |
| 7 | Configuration | Config file path and env vars, from `.env.example` or the config loader. A real example | | x | x | `env` |
| 8 | Integrations | Shell, editor, or other-tool setup, only when the repo documents it | | | x | |
| 9 | Exit codes | Only when the source defines them | | | x | |
| 10 | Development | Clone, install, test commands from scripts or targets | | | x | `commands` |
| 11 | Contributing | One line linking `CONTRIBUTING.md` if it exists | | | x | |
| 12 | License | The license named by `LICENSE` or the manifest | x | x | x | `license` |

## Depth tiers

- **Minimal:** title, opening, install, one usage example, license.
- **Standard:** adds demo, options, and configuration.
- **Full:** adds integrations, exit codes, development, and contributing.

## Rules

- Read flags and subcommands from the argument parser in source (a parser definition, a command table, a derive struct). Never run the binary for its help text.
- Do not write a platform-specific install line the repo does not support. A package-manager line needs a manifest or formula that shows it.
- Time to first success: count the commands from clone to a working result and report it in review. Do not edit the README to hide a long setup.
- Benchmarks and speed claims need a benchmark file or results file in the repo. Link it.
- Table of contents: add a `toc` region when the README exceeds about 1000 words.

## Facts to read

Manifest, lockfile, the argument parser, `bin/` or `cmd/`, release and CI workflows, `Dockerfile`, tests, `.env.example`, `LICENSE`.
