# Monorepo README

A repo with several packages or apps. Signals: workspaces in a manifest, `pnpm-workspace.yaml`, or several manifests under one root. Adapted from the monorepo skeleton of the readme skill (Christopher Bischoff) and the monorepo section of `povvo/claudikins-github-readme-for-perfectionists` (MIT, Ethan Lee). This file holds slots only. Fill every slot from a repo file, or omit the section.

The root README is a router. It says what the whole repo is, lists the packages, and shows how to work across them. Each package keeps its own README for its own detail.

## Section order

| # | Section | Slot | Min | Std | Full | Region |
|---|---|---|---|---|---|---|
| 1 | Title and badges | `{repo name}`. Badges gated by `badges.md` | x | x | x | `badges` |
| 2 | Opening | One sentence: what the whole repo is | x | x | x | |
| 3 | Packages | A table: package path (linked), one-line description. Source: workspace globs, each package manifest `description` | x | x | x | `structure` |
| 4 | Getting started | The root install and the workspace command to run or build across packages, from root scripts and the tool config | x | x | x | `quickstart` |
| 5 | Commands | Root scripts, and the filter form for one package, from the workspace tool's config | | x | x | `commands` |
| 6 | Architecture | How packages depend on each other, from workspace dependency edges. A diagram only when the edges are clear | | | x | |
| 7 | Releasing | Only when a release workflow or config exists. Name the tool and the file | | | x | |
| 8 | Contributing | One line linking `CONTRIBUTING.md` if it exists | | | x | |
| 9 | License | The license named by the root `LICENSE`. Note a package with its own different license if its manifest says so | x | x | x | `license` |

## Depth tiers

- **Minimal:** title, opening, packages table, getting started, license.
- **Standard:** adds commands.
- **Full:** adds architecture, releasing, and contributing.

## Rules

- List a package only if its manifest exists. A folder with no manifest is not a package.
- A private package gets no registry install line. Say it is internal, if its manifest says so.
- The package manager comes from the root lockfile. Do not mix commands from two managers.
- Do not copy package README text into the root README. Link it.
- A package without its own README is a finding for the author, not something to fill by guessing.
- Table of contents: add a `toc` region when the README exceeds about 1000 words.

## Facts to read

Root manifest and lockfile, workspace config, each package manifest and README, root scripts, task-runner config, CI workflows, `LICENSE`.
