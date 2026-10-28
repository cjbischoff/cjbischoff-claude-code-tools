# Perspective interview

Use this in `interview` mode, or when an authored draft has a real substance gap. The goal is to collect language and material the writer actually supplies, not to simulate a human voice.

**Never draft before the writer answers.**

Use the interview when the writer can answer and the text fails this test: could anyone with the same one-line request have written it? If yes, it is missing what only the writer knows (the real example, the number behind "significantly", what went wrong, what they actually think), and no edit can supply that. This is the usual case for posts, newsletters, essays, bios, talk abstracts, pitch emails, landing pages, job posts, and launch stories. Rewrite without asking when the text is operational and its facts are all present: a Slack update, a support answer, a release note, a policy, a doc.

## Step 1: one unorganized take

Ask the writer for one untidied answer before drafting:

> Talk to me for three to five minutes, or stream-type one take. Do not organize it first. Tell me what happened, why you want to write this now, who you want to reach, what you believe, and the examples or doubts that make the idea yours. Use real names, numbers, and incidents only when you are comfortable publishing them. Skip private details instead of blurring them.

Offer these prompts as aids, not a questionnaire the writer must complete:

- What triggered the piece this week: a conversation, bug, meeting, result, or annoyance?
- Picture one reader. What do they already know, and what should change for them afterward?
- Who disagrees with you, and what is their strongest real argument?
- What do you say about this in conversation that you have never written down?
- Which example from your own work carries the point? What happened and what changed?
- Where are you uncertain, or what have you changed your mind about?
- What would you cut from the conventional version of this piece?

Also ask for prior writing on the topic: posts, notes, talks, definitions, or lists the writer already wrote. Treat those as source text and retain their attribution.

## Step 2: at most 5 follow-up questions

After the answer, list the gaps a reader would feel: the real example, the number, the name, what happened, what the writer actually thinks, what they would tell a friend. Then ask at most 5 follow-up questions, in one round.

- **Each question fills a gap a reader would feel.** Quote the line the answer will replace.
- **Ask for narration, not a form.** "In two or three sentences, the way you'd say it out loud: what happened the first time a customer used it?" beats "Please provide a customer example."
- **Make it cheap.** Each question is answerable in under a minute. Say the writer can skip any.
- **Never ask about tone, audience, or format** unless you truly cannot infer it.
- One concrete follow-up usually yields more than five general questions. Prefer: "Tell me about the last time this actually bit you. What broke, and what did you do?"

Skip this step when the answer already covers the point, the example, and what the reader should do.

### If a draft already exists

Do not interview the writer about the whole draft. Ask at most three questions about the parts that lack support or authorship:

```txt
This paragraph says [claim]. What is your evidence, and how sure are you?
The example could belong to anyone. What is your version of it?
The ending restates the point. What should the reader actually do, notice, or reconsider?
```

### If the writer gives you notes or a voice memo

Notes, a voice-memo transcript, or a rough draft the writer wrote themselves are the main material, not background for an AI draft. They already carry the writer's reasoning, and readers and detectors recognize a writer by their reasoning: their claims, the order they make them in, their "because" and "so", their examples.

- **Their structure is the skeleton.** Keep their claim order, their because/so links, their examples where they put them. If they argue A because B, so C, the piece goes A, B, C, not an AI draft's order.
- **Their sentences stay whole where possible.** Edit only for clarity, grammar, and length; keep their odd word choices.
- **An AI draft, if there is one, is a checklist of points only.** It may add a point the writer's notes confirm, placed where it fits their argument. Never borrow its skeleton, transitions, or framing.
- **The notes are the source for the fact audit.** Every fact, commitment, and caveat in the writer's notes must survive. A fact that appears only in the AI draft is optional: keep it where it supports the writer's argument, drop it where it does not. It must still be accurate, and you may not add anything that is in neither.
- **Ask only what the notes leave open.** If they already cover the point, the example, and what the reader should do, write without asking.

## Step 3: turn the answer into prose

1. Extract the point, useful phrases, examples, uncertainties, and order of discovery.
2. **Their sentences are the material.** Build the spine from the writer's supplied language. Keep their phrasing, their order, their odd word choices. Cut true repetition and direct address to the interviewer. Reorder when it clarifies development. Rewording keeps the writer's fingerprint; recomposing replaces it with yours. Preserve distinctive phrases and the order of discovery when they carry voice.
3. Lightly edit grammar when comprehension requires it. Protect coined language, trade slang, genuine asides, mixed feelings, and unusual details. If a stronger edit changes the thought or erases a distinctive phrase, preserve it or show the writer both versions.
4. Add model-written material only for a clear job: sourced research, a definition, a factual bridge, or compression. Model-written research or connective prose must stay source-grounded and visibly separable from personal experience. Never write a memory, preference, or experience for the writer.
5. **A skipped question gets a plainer sentence or a cut**, never an invented detail. Where the piece needs material the interview did not provide, leave `[TK: precise question]`.
6. Where the writer and an AI draft disagree, the writer wins.
7. Run the final checks in `rewrite.md` (fact audit against the writer's answers and notes, mechanical sweep, shorter option).

## Provenance note

Outside the publishable draft, report a provenance note in chat. For a named file, keep it out of the file.

```txt
Provenance:
Author material: [which sections or kinds of language came from the interview or prior writing]
Model contribution: [research, organization, connective prose, or none]
Open items: [TK questions or none]
```

Do not report a detector score as proof of authorship. The provenance note describes the actual process, which is the claim the workflow can support.
