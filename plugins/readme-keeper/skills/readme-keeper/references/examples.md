# Annotated examples

Three real AI/ML capstone READMEs. Each shows a different part of the [AI/ML framework](types/ai-ml.md). Read them to see what "done well" looks like before drafting. Adapt the shape. Never copy the content or the facts: every fact in your README must trace to your own repo.

Source: these examples and their annotations come from the readme skill by Christopher Bischoff. That skill adapts Alexey Grigorev, "How to Write a Good README", which cites all three projects as exemplars. The READMEs are the work of their authors. The links point to them.

## 1. AI Diet Coach: problem, demo, architecture, monitoring

`github.com/thetsuwin66/ai-diet-coach-agent`

**Strong at:** a concrete problem statement with a specific underserved user, a live demo, realistic example prompts, a Mermaid architecture diagram, and rich monitoring.

**Title and problem.** It names the user and the gap in the first lines, then narrows to a specific audience that Western-centric tools underserve. There is no technology opener.

**Demo as usage guide.** Instead of prose, it groups real example prompts by capability. The same block is a demo and a how-to:

```markdown
### Recipe recommendations
What Thai dishes do you have?
Give me a high-protein dinner idea
I want something with chicken that's under 500 calories
```

**Architecture.** A Mermaid `flowchart` maps UI to agent loop to tools to knowledge base and APIs. Each node carries its real file name. A table lists the 9 agent tools and what each does.

**Evaluation with a decision trail.** It shows why TF-IDF won over embeddings: a pros and cons table and a Hit@3 comparison. It then documents 4 iterations of an LLM judge, with an accuracy, precision, recall, and F1 table per version and a note on what each change fixed. This is the "baseline, then change, then final" story the framework asks for.

**Monitoring.** It states what each trace captures (question, tool calls, tokens, latency, feedback), where traces are stored (`data/traces/*.json`), and both dashboards (a built-in Streamlit tab and Logfire), with a panel-by-panel table.

**Reproducibility.** One copy-paste block takes a clean clone to a running, tested, evaluated project. It notes that the data is included and that no external download is needed.

## 2. Research Radar: one-liner, evaluation and tuning, CI, tests

`github.com/55382/Research_Radar_agent_phd_assistant`

**Strong at:** a one-sentence description, evaluation tied to parameter tuning, real test counts, and an explicit feedback loop.

**Description.** One sentence carries the user, the problem, the solution, and the feedback mechanism: it monitors ArXiv daily, ranks by the reader's interests with RAG, emails a digest, and learns from ratings given in the email.

**Metrics explained, not only reported.** A table defines Precision@K, Recall@K, and NDCG@K in plain language ("what it measures" and "what a good value means") before it shows numbers. It then shows how evaluation drove tuning:

```markdown
| Change tested | NDCG@5 before | NDCG@5 after |
|---|---|---|
| {parameter change} | {value} | {value} |
```

**Testing.** It states the real test count, separates unit tests from LLM-judge satisfaction tests, and shows the actual `-s` output, including a rating histogram.

**Environment variables.** A required and optional table, plus a note that a free provider works with no setup. That removes a setup blocker.

**Feedback loop.** It spells out the closed loop: email rating, feedback server, CSV, profile rebuild, better rankings. Each rating improves the next digest and grows the evaluation ground truth.

## 3. CineRAG: two evaluations, datasets, containers

`github.com/bielacki/cinerag`

**Strong at:** two separate evaluations (retrieval quality and answer quality), each with its own dataset, metrics, and results. Thorough env-var docs. Honest limitations.

**Two evaluations, not one.** This is the key difference. The retrieval evaluation compares four backends on Recall@5 and @10, MRR, and nDCG@10, with a results table and an analysis. A separate LLM-as-judge evaluation scores generated answers on relevance, faithfulness, coherence, and aspect coverage, with mean, median, and standard deviation. Each names its dataset file and shows the record format:

```json
{"query": "{a real query from the dataset}", "gold": ["{a real document id}"]}
```

**API documented with real calls.** Endpoints appear with runnable `curl` commands and real request and response JSON, not descriptions.

**Containerization.** A services table (image, port, purpose), the exact `docker compose` commands, and minimum and recommended resources.

**Limitations, stated plainly.** It says the LLM integration is minimal, the evaluation dataset is small, and the app supports English only. This is the boundary-setting the framework asks for, with no apology and no hiding.

**References and attribution.** It credits the data source and its terms, the course, and the papers and technology behind the approach.

## What to take from all three

- Open with user, problem, and solution. Never open with a technology list.
- Evaluation is the center of an AI project: the dataset, a metrics table, and the tuning story from baseline to final.
- Show, do not tell: real prompts, real `curl`, real numbers, real file paths, screenshots.
- Use tables for metrics, env vars, tools, and services. They scan better than prose.
- State gaps under Limitations (no tests, a small dataset, not deployed). Do not imply completeness.
