# NOTICE

readme-keeper adapts material from the sources below. The table lists each adapted file.
Ideas from `tavva/ben-claude-plugins` (`plugins/readme-generator`) are used in new words only:
that repository has no license file, so none of its text is copied.

## Sources

| Source | License | Use |
|---|---|---|
| `~/.claude/skills/readme` by Christopher Bischoff, adapting Alexey Grigorev, "How to Write a Good README" (<https://alexeyondata.substack.com/p/how-to-write-a-good-readme>) and three example projects it cites | User's own skill; article and example credit retained | Create workflow, templates, AI/ML framework, examples |
| <https://github.com/rushikeshsakharleofficial/readme-forge> @ `fd45d6d` | MIT | Type routing, badge gating, lockfile install, decorative image catalog |
| <https://github.com/povvo/claudikins-github-readme-for-perfectionists> @ `1787804` | MIT | Fact report, section order by type, time to joy, won't-do, badge hygiene |
| <https://github.com/cajias/claude-skills> `plugins/dev` @ `53fe021` | MIT | Reader rubric, evaluate mode, tiered issues, score weights |
| plainspoken (this marketplace), carrying clarity by Addy Osmani and work-humanizer by Pawel Huryn | MIT | Safeguards, prose-tell lexicon, severity tiers |

## Adapted files

| readme-keeper file | Adapted from | License |
|---|---|---|
| `skills/readme-keeper/SKILL.md` | User's readme skill `SKILL.md` (workflow, three readers, verify step); claudikins `deep-dive/SKILL.md` (fact report, confidence levels); readme-forge `skills/readme/SKILL.md` (omit empty sections, needs-manual-fill, lockfile install, ask before overwrite) | User's own; MIT; MIT |
| `skills/readme-keeper/references/types/ai-ml.md` | User's readme skill `references/ai-ml-project.md` | User's own (adapts Grigorev) |
| `skills/readme-keeper/references/types/library.md`, `cli.md`, `service.md`, `monorepo.md`, `web-app.md` | User's readme skill `references/templates.md`; claudikins `pen-wielding/references/structural-templates.md` (section order for library, CLI, monorepo) | User's own; MIT |
| `skills/readme-keeper/references/types/plugin.md` | readme-forge `skills/readme/references/patterns/plugin.md` | MIT |
| `skills/readme-keeper/references/rubric.md` | User's readme skill `SKILL.md` (common mistakes, three readers, four questions); cajias `plugins/dev/commands/review-readme.md` (core questions, caveats first, trust signals, severity, score weights; credits banesullivan/README and hackergrrl/art-of-readme); claudikins `crystal-ball/references/roadmap-patterns.md`, `think-tank/references/scoring-rubric.md` (won't do, time to joy) | User's own; MIT; MIT |
| `skills/readme-keeper/references/examples.md` | User's readme skill `references/examples.md` | User's own (adapts Grigorev and three example projects) |
| `skills/readme-keeper/references/badges.md` | readme-forge `skills/readme/references/01-badges.md` (catalog, fact gates, decorative images); claudikins `think-tank/references/badge-ecosystem.md` (hygiene) | MIT; MIT |
| `skills/readme-keeper/references/safeguards.md` | plainspoken `skills/plainspoken/SKILL.md` "Shared safeguards" | MIT (clarity, work-humanizer) |
| `skills/readme-keeper/references/tells.md`, `skills/readme-keeper/scripts/check.py` (prose lexicon, comment stripping, sync and hostile-input test patterns) | plainspoken `references/tells.md`, `scripts/lint.py` | MIT (clarity, work-humanizer) |
| `evals/JUDGE.md` | plainspoken `evals/JUDGE.md` | MIT (clarity) |

## Licenses

### readme-forge

Copyright notice and license of rushikeshsakharleofficial/readme-forge:

```text
MIT License

Copyright (c) 2026 Rushikesh Sakharle

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### claudikins-github-readme-for-perfectionists

Copyright notice and license of povvo/claudikins-github-readme-for-perfectionists:

```text
MIT License

Copyright (c) 2025 Ethan Lee

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### cajias/claude-skills

Copyright notice and license of cajias/claude-skills:

```text
MIT License

Copyright (c) 2024 Claude Skills Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### clarity

Copyright notice and license, reached through plainspoken:

```text
MIT License

Copyright (c) 2026 Addy Osmani

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### work-humanizer

Copyright notice and license, reached through plainspoken:

```text
MIT License

Copyright (c) 2026 Pawel Huryn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
