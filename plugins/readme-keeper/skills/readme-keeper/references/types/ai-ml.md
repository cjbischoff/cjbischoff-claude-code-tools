# AI/ML project README framework

For RAG apps, agents, and LLM-powered projects, and for course projects, portfolio projects, and anything reviewed against a rubric. Signals: an LLM or embedding dependency, a vector store, an `eval/` or `evals/` folder, prompt files. Adapted from the `ai-ml-project.md` framework of the readme skill by Christopher Bischoff, which adapts Alexey Grigorev, "How to Write a Good README". Sample facts, numbers, and example text are removed. This file holds slots only. See `../examples.md` for three READMEs that do each part well.

A reader of an AI/ML project asks four questions in order. The sections map to them. Include only what the project earns. Omit a section, or note the gap under Limitations, instead of faking it.

| Part | Question | Sections |
|---|---|---|
| 1 | What is this project? | Title and description, Problem, Demo |
| 2 | Does it work well? | Evaluation, Testing, Monitoring |
| 3 | Can I run and reproduce it? | Quickstart, Data and configuration, Deployment |
| 4 | How was it built? | Architecture, Project structure, Decisions, CI/CD |
| Extra | | Limitations, Future work, Self-evaluation |

## Section order (16 sections)

| # | Section | Slot | Min | Std | Full | Region |
|---|---|---|---|---|---|---|
| 1 | Title and description | See below | x | x | x | `badges` |
| 2 | Problem | The user's goal, what makes it hard, why existing options fall short, who has the problem | x | x | x | |
| 3 | Demo | Live link, video, GIF, screenshots, or sample input and output that exist in the repo or that the author supplies | x | x | x | |
| 4 | Evaluation | Dataset, metrics, progression, how to rerun | | x | x | |
| 5 | Testing | Which tests exist and the one command | | x | x | `commands` |
| 6 | Monitoring | What is captured, where it is stored, how to view it | | | x | |
| 7 | Quickstart | Prerequisites, clone, install, env, services, start | x | x | x | `quickstart` |
| 8 | Data and configuration | External inputs, the env example, required versus optional variables | | x | x | `env` |
| 9 | Deployment | Where it is hosted, services, how it deploys | | | x | |
| 10 | Architecture | A diagram of data and requests, plus a short prose explanation | | x | x | |
| 11 | Project structure | A simplified tree with one-line purposes | | x | x | `structure` |
| 12 | Decisions and trade-offs | Choice, reason, downside, why accepted | | | x | |
| 13 | CI/CD | Triggers, checks, failure behavior, deploy | | | x | |
| 14 | Limitations | Specific boundaries and consequences | x | x | x | |
| 15 | Future work | Prioritized, follows from the limitations | | | x | |
| 16 | Self-evaluation | Each rubric criterion, the score the author believes it earns, the evidence. Course projects only | | | x | |

The install, license, and table of contents regions follow the other type references: `install` inside Quickstart, `license` as a last section, `toc` above 1000 words.

## Depth tiers

- **Minimal:** title, problem, demo, quickstart, limitations, license.
- **Standard:** adds evaluation, testing, data and configuration, architecture, and structure.
- **Full:** adds monitoring, deployment, decisions, CI/CD, future work, and (for a course) self-evaluation.

## Part 1: What is this project?

### 1. Title and description

One or two sentences that name the **user, the problem, and the solution**. Do not open with a technology list: it says what was used, not what it does.

Starting formula:

> **{Project name}** is a **{type of system}** that helps **{specific user}** do **{task or outcome}**.

Add a second sentence on the obstacle or why it matters. Keep it concrete: "AI-powered platform" and "intelligent solution" say nothing. If a deployment exists, put the live link under the title.

### 2. Problem

Explain the problem the description introduced:

1. What is the user trying to do?
2. What makes it difficult?
3. Why are existing options insufficient?
4. Who experiences this?

Keep it proportional: a few specific paragraphs, not a market analysis. State the target user. This section needs the author's words. If the repo does not answer it, ask.

### 3. Demo

Show it working before asking anyone to install anything. Use what best represents it: a live link, a short video, a GIF, screenshots, or sample input and output. For an AI app, show the core loop: request, retrieval or processing, answer, follow-up or feedback. Realistic example prompts double as a demo and a usage guide. If deployed, keep screenshots too, because hosted demos disappear. Never invent output: use real captures or ask.

## Part 2: Does it work well?

This part separates a real AI project from a demo.

### 4. Evaluation

Without it, a reader sees answers and cannot judge quality. Cover:

- **Dataset:** what it contains and how it was built (hand-labeled or generated: say which). It should reflect real usage, not only easy cases.
- **Metrics:** the actual numbers from a results file in the repo. Retrieval: hit rate, Precision@K, Recall@K, MRR, NDCG@K. End to end or LLM-as-judge: relevance, faithfulness, coherence, aspect coverage. Use only the metrics the repo computes.
- **Progression:** baseline, then what changed, then final. The tuning story is the valuable part.
- **How to rerun:** the command, and a link to the notebook or script and the results file.

Summarize in the README with a results table. Keep detailed code and results in a clearly named location and link them. Every number traces to a file.

```markdown
| {Variant} | {Metric 1} | {Metric 2} | {Metric 3} |
|---|---|---|---|
| {baseline} | {value from results file} | {value} | {value} |
| {final} | {value from results file} | {value} | {value} |
```

No evaluation exists: do not write the section. Say so under Limitations. An AI app without evaluation is a demo.

### 5. Testing

State which tests exist and the single command to run them. If they need a service, an API key, or a container, say so before the command, so the reader does not learn it from an error. If there are no automated tests, say so plainly and list it under Limitations. Honesty beats implied completeness.

### 6. Monitoring

Evaluation measures a prepared dataset. Monitoring measures real traffic. Describe: the metrics captured (latency, tokens, cost, feedback, tool usage), where they are stored, and how to view them. If there is a dashboard, include a screenshot and explain the panels. Only describe what the code records.

## Part 3: Can I run and reproduce it?

### 7. Quickstart

The shortest reliable path from a clean machine to a running app. Include prerequisites, clone, install, env config, required services, and the start command, in the order the repo's own scripts and docs show. Name core tools and versions from the manifests: the language version, the package manager the lockfile shows, containers, a Node version if there is a frontend, non-containerized system dependencies. If there are several setup methods, show the recommended one first. Add **Local development** (running services separately) and **Troubleshooting** when the repo documents them.

### 8. Data and configuration

Projects often fail to run because the data or config is missing. Document every external input: source, file, destination, and the command that fetches or builds it.

List each environment variable and what it controls. Provide the env example file if one exists. State which are **required** and which **optional** (can it start without the monitoring service or a third-party API?). Use a table:

```markdown
| Variable | Required | Description |
|---|---|---|
| `{NAME from .env.example}` | {Yes or No} | {what it controls} |
```

### 9. Deployment

If deployed, the live URL goes near the top and this section explains where it is hosted, which services it uses, how deployment works (manual or CI/CD), the required secrets by name, and how someone else could deploy their own. If several services connect, describe how. If it is not deployed, say so and give the local alternative.

## Part 4: How was it built?

### 10. Architecture

Show how data and requests flow through the system: a Mermaid diagram, an image, or a text flow. Add a short prose explanation, because a diagram shows relationships and not why a component exists. Label nodes with real file or service names from the repo.

```mermaid
flowchart LR
    {Component A} --> {Component B} --> {Component C}
```

### 11. Project structure

A simplified file tree with one-line descriptions: enough to find the code behind each claim, not the full `tree` output with every generated file. Say which notebook or script holds the reported results.

### 12. Decisions and trade-offs

The reasoning matters more than the technology list. Format:

> I chose **{X}** over **{Y}** because of **{constraint}**. The downside was **{A}**. I accepted it because **{B}**.

Only the author can write this. Ask for it. Never infer a reason from the dependency list.

### 13. CI/CD

What triggers the workflow, which checks run, what happens on failure, whether success deploys. AI evaluations are slow and costly, so a small set on pull requests and the full suite before release is a valid pattern, if the workflow does it. Link the workflow files. No CI/CD: do not imply any, and note it under Limitations.

## Extra sections

### 14. Limitations

What the project does not handle well: specific, a boundary and its consequence. State it plainly. Do not hide it in vague wording and do not turn it into an apology. Only the author states limitations. `create` may list candidates it saw (no tests, no CI, no evaluation) under "Needs manual fill".

### 15. Future work

Follows from the limitations or from evidence gathered while building. Realistic and prioritized: what would change and why. Future tense only.

### 16. Self-evaluation

For a course project: go through each rubric criterion, state the score the author believes it earns, and point to the evidence. It helps the reviewer navigate. Do not award points without evidence. The reviewer still judges independently. Skip this section unless the user names a rubric.

## Skeleton

```markdown
# {Project name}

{Name} is a {type of system} that helps {user} do {task}. {Why it matters.}

**Live demo:** {url}  |  **Video:** {url}

## Problem
{User goal, what is hard, why existing options fall short, who has this problem.}

## Demo
{Screenshot, GIF, example prompts, or sample input and output.}

## Evaluation
{Dataset, metrics table, baseline to final progression, how to rerun with a link.}

## Testing
{What is tested, prerequisites, the one command. Or: "no automated tests" (see Limitations).}

## Monitoring
{Metrics captured, where stored, how to view, dashboard screenshot.}

## Quickstart
{Prerequisites, clone, install, env, services, run.}

## Data and configuration
{External data steps, env example, required and optional variables.}

## Deployment
{Where hosted, services, CI/CD, how to deploy your own. Or a local-only note.}

## Architecture
{Diagram and a short explanation of the flow.}

## Project structure
{Simplified tree with one-line descriptions.}

## Decisions and trade-offs
{X over Y because Z. Downside A. Accepted because B.}

## CI/CD
{Triggers, checks, failure behavior, deploy. Or a note on absence.}

## Limitations
{Specific boundaries and consequences.}

## Future work
{Prioritized, follows from the limitations.}

## License
{License named by LICENSE.} See [LICENSE](LICENSE).
```

The skeleton is a slot map, not a mold. Delete every section the project has not earned. A `{slot}` with no repo source is a "Needs manual fill" entry in chat. It is never left in the file.
