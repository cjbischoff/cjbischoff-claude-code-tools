# Service README

A web service, API, or long-running process. Signals: a web framework dependency plus a server entry point. Adapted from the service skeleton of the readme skill (Christopher Bischoff). This file holds slots only. Fill every slot from a repo file, or omit the section.

The main friction for a service reader is setup: runtime, databases, secrets, and the first successful request.

## Section order

| # | Section | Slot | Min | Std | Full | Region |
|---|---|---|---|---|---|---|
| 1 | Title and badges | `{service name}` from the manifest. Badges gated by `badges.md` | x | x | x | `badges` |
| 2 | Opening | One sentence: what the service does and who calls it | x | x | x | |
| 3 | Prerequisites | Runtime version, databases, queues, and external services the code requires, from manifests, compose files, and config | | x | x | |
| 4 | Getting started | Clone, install, copy the env example, run the real dev script. Order from the repo's own scripts | x | x | x | `quickstart` |
| 5 | Local address | The default host and port, from the server entry point or config. Ask if the code does not show it | x | x | x | |
| 6 | Environment variables | A table: name, required or optional, one-line purpose. Source: `.env.example` or the config loader | | x | x | `env` |
| 7 | API | The routes or operations from route definitions or an OpenAPI file. Link the spec file if one exists. A runnable request only if the repo shows one | | x | x | |
| 8 | Scripts | The scripts users need (dev, build, test, lint), verbatim | | x | x | `commands` |
| 9 | Architecture | A diagram of the parts and how they connect, only when the code shows the parts | | | x | |
| 10 | Project structure | A simplified tree with one-line purposes | | | x | `structure` |
| 11 | Deployment | How it deploys, from a `Dockerfile`, compose file, CI deploy workflow, or platform config. Omit if none exists | | | x | |
| 12 | Testing | The test command, and what it needs (a service, a key, a container), stated before the command | | x | x | `commands` |
| 13 | Limitations | Boundaries the author states | | | x | |
| 14 | License | The license named by `LICENSE` or the manifest | x | x | x | `license` |

## Depth tiers

- **Minimal:** title, opening, getting started with the address, license.
- **Standard:** adds prerequisites, env table, API, scripts, and testing.
- **Full:** adds architecture, structure, deployment, and limitations.

## Rules

- State required prerequisites before the command that needs them.
- A secret has a name and a purpose in the README. Never a value.
- Do not claim a deployment, a hosted URL, a health endpoint, or a rate limit the repo does not show.
- Do not start the service to learn its address or routes. Read the source.

## Facts to read

Manifest, lockfile, the server entry point, route definitions, OpenAPI file, `.env.example`, `Dockerfile` and compose files, migrations, CI workflows, tests, `LICENSE`.
