# Web app README

A browser application. Signals: a frontend framework dependency plus an app entry (a pages or app folder, an HTML entry, a bundler config). A repo with both a frontend and a server entry is a monorepo or a service: check the type table order first. Adapted from the service skeleton of the readme skill (Christopher Bischoff). This file holds slots only. Fill every slot from a repo file, or omit the section.

A web-app reader wants to see it, then run it. Put a demo before setup.

## Section order

| # | Section | Slot | Min | Std | Full | Region |
|---|---|---|---|---|---|---|
| 1 | Title and badges | `{app name}` from the manifest. Badges gated by `badges.md` | x | x | x | `badges` |
| 2 | Opening | One sentence: what the app does and who uses it. Live link here if the author supplies one | x | x | x | |
| 3 | Demo | A screenshot or GIF that exists in the repo, or the live URL the author confirms. Ask if none | | x | x | |
| 4 | Features | One true sentence per capability the code has | | x | x | |
| 5 | Prerequisites | Runtime version and tools from `engines` or version files | | x | x | |
| 6 | Getting started | Install, copy the env example, run the real dev script | x | x | x | `quickstart` |
| 7 | Local address | The dev server default from config or scripts. Ask if the code does not show it | x | x | x | |
| 8 | Environment variables | A table: name, required or optional, purpose. Public (client-exposed) and private values in separate rows or tables | | x | x | `env` |
| 9 | Scripts | dev, build, test, lint, verbatim | | x | x | `commands` |
| 10 | Project structure | A simplified tree with one-line purposes | | | x | `structure` |
| 11 | Deployment | How it deploys, from platform config, a `Dockerfile`, or a CI deploy workflow. Omit if none | | | x | |
| 12 | Browser support | Only when a browserslist or equivalent config states it | | | x | |
| 13 | Contributing | One line linking `CONTRIBUTING.md` if it exists | | | x | |
| 14 | License | The license named by `LICENSE` or the manifest | x | x | x | `license` |

## Depth tiers

- **Minimal:** title, opening, getting started with the address, license.
- **Standard:** adds demo, features, prerequisites, env table, and scripts.
- **Full:** adds structure, deployment, browser support, and contributing.

## Rules

- The stack list is not an opening. If the stack is useful, give it its own line after the opening, read from dependencies.
- A client-exposed env var is public by definition. Never show a value. Say which names the build exposes.
- Do not claim accessibility, performance scores, or browser support without a config or report in the repo.
- Screenshots go in the repo or the author's host. Never link a screenshot you did not see in the repo.
- Table of contents: add a `toc` region when the README exceeds about 1000 words.

## Facts to read

Manifest and lockfile, framework and bundler config, the app entry, `.env.example`, scripts, `Dockerfile`, platform config, CI workflows, tests, `LICENSE`.
