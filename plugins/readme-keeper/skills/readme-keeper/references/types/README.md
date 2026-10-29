# references/types/

One reference per project type. `create` loads the one that matches the repo. `review` loads it to know which sections to expect. Each file holds the section order, the depth-tier rules (minimal, standard, full), and slot descriptions. No file holds sample facts: no example flags, stacks, endpoints, metrics, or license names. Every slot is filled from a repo file or left out.

`SKILL.md` holds the precedence table. The first matching row wins.

| File | Type | Signals |
|---|---|---|
| `plugin.md` | Claude Code plugin or marketplace | `.claude-plugin/plugin.json` or `marketplace.json` |
| `ai-ml.md` | AI/ML project (the 16-section framework) | LLM or embedding dependency, vector store, `eval/` or `evals/`, prompt files |
| `monorepo.md` | Monorepo | Workspaces, `pnpm-workspace.yaml`, several manifests |
| `cli.md` | CLI | `bin` in `package.json`, `[project.scripts]`, `[[bin]]`, `cmd/` in Go |
| `service.md` | Service or API | Web framework dependency and a server entry point |
| `web-app.md` | Web app | Frontend framework and an app entry |
| `library.md` | Library | Default when a manifest exists |

## Attribution

`ai-ml.md`, `library.md`, `cli.md`, `service.md`, and `monorepo.md` adapt the readme skill by Christopher Bischoff. `ai-ml.md` adapts Alexey Grigorev, "How to Write a Good README". `library.md`, `cli.md`, and `monorepo.md` also adapt the section order of `povvo/claudikins-github-readme-for-perfectionists` (MIT, Ethan Lee). `plugin.md` adapts the plugin pattern of `rushikeshsakharleofficial/readme-forge` (MIT, Rushikesh Sakharle). `web-app.md` is new, based on the service skeleton. See `../../../NOTICE.md`.
