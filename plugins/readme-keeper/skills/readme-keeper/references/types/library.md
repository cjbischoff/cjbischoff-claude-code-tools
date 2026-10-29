# Library README

A package that other code installs and imports. The default type when a manifest exists and no other row of the type table matches. Adapted from the library and section-snippet skeletons of the readme skill (Christopher Bischoff) and the section order for libraries in `povvo/claudikins-github-readme-for-perfectionists` (MIT, Ethan Lee). This file holds slots only. Fill every slot from a repo file, or omit the section.

The main friction for a library reader is understanding the model, not installing. Put real code early.

## Section order

`x` marks the depth tiers that include the section. Region is the marker id for generated content.

| # | Section | Slot | Min | Std | Full | Region |
|---|---|---|---|---|---|---|
| 1 | Title and badges | `{package name}` from the manifest. Badges gated by `badges.md` | x | x | x | `badges` |
| 2 | Opening | One sentence: what it is. One sentence: the problem it solves. Source: manifest description, module docstring, the author's answer | x | x | x | |
| 3 | Features | One true sentence per feature the code has. No adjectives with no measurement | | x | x | |
| 4 | Install | The install command for the package manager the lockfile shows, with the real package name | x | x | x | `install` |
| 5 | Usage | A minimal example using real exported names, copied from tests, examples, or docs in the repo | x | x | x | |
| 6 | API | The main public functions or classes and what each does. Link to fuller docs if they exist | | x | x | |
| 7 | Configuration | Options and defaults, from the config schema or code. A table for 3 or more options | | | x | `env` when env vars |
| 8 | Compatibility | Runtime or language versions from `engines`, `requires-python`, `rust-version`, or the `go` directive | | x | x | |
| 9 | Development | Clone, install, test, lint commands from scripts or targets | | | x | `commands` |
| 10 | Contributing | One line linking `CONTRIBUTING.md` if it exists. Never create that file | | | x | |
| 11 | Limitations | Boundaries the author states. Never inferred | | | x | |
| 12 | License | The license named by `LICENSE` or the manifest, linking the file | x | x | x | `license` |

## Depth tiers

- **Minimal:** title, opening, install, usage, license. Aim for one screen.
- **Standard:** adds features, API summary, and compatibility.
- **Full:** adds configuration, development, contributing, and limitations. Move long optional detail into `<details>`.

## Rules

- The first code block a reader sees is a working example, not a list of technologies.
- Use real names from the code. A placeholder like `foo` is a finding.
- Show expected output when the example produces output and the repo shows it.
- Table of contents: add a `toc` region when the README exceeds about 1000 words. Below 500 words, omit it.
- No performance, size, or "zero dependency" claim without a source: a benchmark file, a lockfile, or a manifest `dependencies` that is empty.
- Several entry points or packages: use `monorepo.md` instead.

## Facts to read

Manifest (`name`, `version`, `description`, `exports` or `main`, `engines`, `license`, `repository`), lockfile, public entry point, `examples/`, tests, `docs/`, `LICENSE`, CI workflows.
