# Reader rubric

Used by `review`. Also used by `create` to check the opening of the draft. Adapted from the readme skill by Christopher Bischoff (the four questions, the three readers, the common mistakes) and from the `review-readme` command in `cajias/claude-skills` `plugins/dev` (MIT, Claude Skills Contributors: the core questions, caveats first, trust signals, tiered issues, score weights). The core questions in that command come from banesullivan/README, and its method follows hackergrrl/art-of-readme. The "won't do" idea adapts the roadmap patterns of `povvo/claudikins-github-readme-for-perfectionists` (MIT, Ethan Lee).

## The four questions

A README reader asks these in order. Each question maps to sections.

| Question | The README must show | Typical sections |
|---|---|---|
| What is this? | What it does, for whom, why it matters. No technology list as the opening. | Title, opening, demo |
| Does it work? | Evidence from the repo: tests, a CI workflow, results, a demo. | Testing, evaluation, status, badges |
| Can I run it? | Prerequisites, then the shortest path from a clean clone to a working result. Commands match the repo. | Install, quickstart, config |
| How is it built? | The parts, how they connect, and why. | Architecture, structure, decisions |

## Three readers at once

Their needs stack. They do not conflict.

- **Reviewer or grader.** Needs evidence for each claim. Do not make them dig through notebooks.
- **Hiring team.** Skims. Needs a clear opening and a reason to continue within seconds.
- **Future self.** Returns in six months. Needs enough context to resume without reverse-engineering the code.

## Reader rules

- **Caveats first.** Limits, prerequisites, platform and version requirements, and known gaps appear before the step that needs them. A caveat buried at the end is a finding.
- **Cognitive funnel.** Order runs broad to specific: overview, then usage, then detail. Collapse long optional detail (migration guides, full config references) in `<details>`. Never collapse install, basic usage, or a critical warning.
- **Trust signals.** A CI status, a license, a version, a test command, and an honest limitations list build trust. Each must be true. A badge for a thing that does not exist is a P1 under Badges in `check.py`.
- **Time to first success.** Count the commands from clone to a working result. Report the count. When it is more than five, suggest a Makefile, justfile, or container setup as a fix to the project, not as an edit to the README.
- **Visual density.** Prose with no code block, table, diagram, or image for a long stretch is a scan problem. Report it as P2.
- **Show, do not tell.** Real command names, real paths, real output. Not `foo` and `bar`.

## Common mistakes

- **No setup instructions.** A project that cannot run from a clean clone fails reproducibility.
- **No demo.** A reader who must run the code to see it will often leave. A screenshot, GIF, live link, or sample input and output near the top fixes it. Do not invent one: ask for it.
- **No evaluation (AI projects).** An AI app without evaluation is a demo.
- **Work buried in notebooks.** Link results from the README.
- **Stale README.** Commands, numbers, screenshots, and links must match the current version.
- **Wall of text.** Use sections, tables, commands, and diagrams.
- **Planned work described as done.** Planned work goes under Future work.
- **Technology list as the opening.** It says what was used, not what it does.
- **Opening that fits any project.** "A powerful tool for developers" says nothing.

## Won't do

A project can state what it will not do, with the reason and an alternative. It lets readers self-select and helps maintainers decline off-scope requests. Only the maintainer can write it. `review` may suggest the section when issues or docs show repeated off-scope requests. It never drafts the entries.

## Severity

One list. It matches the `check.py` severities, so a reader sees one scale.

**P0: false or unrunnable.** The reader acts on it and fails, or loses trust.
- A command, or a link or image, in the README that points to something that does not exist in the repo (any `check.py` P0)
- A license name that no `LICENSE` file or manifest field supports
- A broken or unpaired marker
- No way to run or use a runnable project, with no statement that this is the case
- Planned work stated in the present tense as if it exists

**P1: misleads or blocks.**
- The package manager in an install command differs from the lockfile
- A broken anchor, or a 4xx external link
- A badge whose source is missing or stale
- The opening does not say what the project is or who it is for
- Prerequisites appear after the step that needs them
- A section that the project's type reference expects is missing with no note
- A claim with no evidence in the repo or README (a quality claim, a performance claim)

**P2: polish.**
- A flaky link (timeout, 5xx)
- Long prose with no visual or code block
- Inconsistent heading depth, a code block with no language tag
- Prose tells flagged by `check.py --prose`
- A table of contents on a short README, or none on a long one
- A section that fits another type's order better

A suggested fix that would add an invented fact is dropped, and the finding names what the author must supply.

## Score (`--score`)

A report value. It is never a loop target and never a gate. The model does not rewrite until the score rises. Report the score next to the open P0 list, never instead of it.

Weights follow `review-readme` (cajias). Each criterion is scored 0-100, then weighted.

| Criterion | Weight | Judges |
|---|---|---|
| Essential sections | 40% | The sections the type reference expects at the chosen depth are present, or their absence is stated. |
| Content quality | 30% | The four questions are answered. Caveats first. Specific and true. |
| Examples | 20% | Code blocks are real, complete, runnable against the repo, and show expected output when it helps. |
| Formatting | 10% | Heading hierarchy, language tags, lists, tables, no broken markup. |

Report format: one line per criterion with its score and the one-line reason, the weighted total, and the P0 count. State that the score is the model's judgment, so it varies between runs.
