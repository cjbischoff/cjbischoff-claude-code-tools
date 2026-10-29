# skills/readme-keeper/

The `readme-keeper` skill. One skill with four modes: `create`, `update`, `check`, and `review`. `create` and `update` write only after the user approves a diff. `check` and `review` never write. `SKILL.md` routes a request to a mode, holds the safeguards, the marker rules, and the steps of each mode, and loads only the reference the mode needs.

## Layout

```text
skills/readme-keeper/
├── README.md         this file
├── SKILL.md          router, safeguards, mode steps, markers; under 200 lines
├── references/       type references, rubric, badges, safeguards, tells (see references/README.md)
└── scripts/
    └── check.py      mechanical README checker, Python 3.11+, stdlib only
```

## How it works

- Every fact in a README traces to a file in the repo. `check.py` verifies commands, paths, anchors, license, badges, and markers against the repo. Markers shown inside code are examples, not regions. `--all` skips test-fixture folders by default.
- `update` regenerates only the regions between `<!-- readme-keeper:start id -->` and `<!-- readme-keeper:end id -->`. Text outside a region is never edited.
- The skill never runs target code, never commits, and never creates a `LICENSE` file.

## Attribution

The create workflow, the type references, and the examples adapt the readme skill by Christopher Bischoff, which adapts Alexey Grigorev, "How to Write a Good README". The reader rubric, badge rules, and fact report draw on `cajias/claude-skills`, `rushikeshsakharleofficial/readme-forge`, and `povvo/claudikins-github-readme-for-perfectionists` (all MIT). The safeguards adapt plainspoken. See `NOTICE.md` at the plugin root.
