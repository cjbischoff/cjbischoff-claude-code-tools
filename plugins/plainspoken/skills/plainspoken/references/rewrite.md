# Rewrite guide

Use this for `rewrite` mode, as the pattern reference in `review` mode, and for the final checks in `interview` mode. Read the passage before classifying a pattern. A familiar construction is not a defect when the surrounding prose earns it or the medium requires it.

Word lists are in `tells.md`. For the mechanical sweep, run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/plainspoken/scripts/lint.py <file>`.

Two things shape everything below:

1. **Readers notice texture.** Emphasis with no information in it, uniform rhythm, generic claims, and sentences that do the reader's thinking for them. Those are fixable by editing.
2. **Specifics carry the human signal.** You may only use specifics that are in the source or that the writer gives you. An assistant model rewording a draft does not change who composed it. If the writer needs text that is genuinely theirs, use `interview`.

## Steps

1. **Read for the job.** Reader, outcome, and register (see "Establish the job of the piece" in `SKILL.md`). Decide where the point goes and commit: answer-first for replies, emails, Slack, and announcements; evidence-first for explanations and arguments. A text that states its point in line 1 and builds to the same point at the end has done both. Cut one.
2. **Diagnose the largest problem, in this order.** Fix in that order:
   1. **Missing substance.** Identify the real outcome or point. In authored long-form work, find the source material only this writer supplied. If it is absent, ask or label the limitation.
   2. **Wrong register.** The text is not the kind of writing its reader needs.
   3. **Weak development.** Make paragraphs depend on one another through cause, contrast, sequence, qualification, example, or consequence. Restructure only as much as the request permits.
   4. **Surface patterns.** Remove inflated, repetitive, or formulaic machinery while preserving useful voice and medium conventions.

   When the draft is hollow, say so in 2-3 sentences and offer `interview`. If the user still wants a rewrite, deliver it and state what editing could and could not repair.
3. **List the facts, with their certainty.** Every number, name, date, claim, commitment, caveat, link, quotation, and call to action, plus the qualifier attached to each ("could", "typically", "about", "helped", "the remaining piece"). Include attribution, examples, terminology, citations, constraints, and redactions. This list must survive intact.
4. **Write it fresh.** Put the draft aside. From your step 3 list, write the piece the way this writer would write it for this reader (see "Sound like a person"): their speaker, their register, plain spoken sentences in normal word order. Do not edit the AI sentences in place; a patched AI draft still reads like one. Reuse the draft's exact words only for names, the reader's own terms, and the wording of commitments and conditions. Fresh wording, same claims: every claim in the draft appears in your version at the same strength, no stronger and no weaker. Preserve meaning and useful voice.
5. **Keep the claim, drop the formula.** A stock line (a generic moral, a value pitch, a gratitude formula, a vague benefit) still carries something the writer meant to say. Say that thing once, plainly, in the writer's voice: "Those visits helped us get here" becomes "We wouldn't have made it ten years without you coming in." Cut a stock line only when it repeats something already said.
6. **Cut and fix the tells** (below, and the lists in `tells.md`), strongest first: a colon reveal, a triad, a stock closer, a generic wrap-up line. Delete filler, restatement, and hype. Cutting must not leave it clipped: if the draft was not padded, your version should be about as long as the draft. Voice, concrete detail, connective words, and the warmth a genre needs are not padding. Let sentences breathe: use the small words people use when they talk (so, and, but, just, then), and never squeeze two ideas into one clipped clause.
7. **Fix rhythm and flow** (section E). Run one self-review pass against the finished text. Fix the weakest material issue once, then stop. Repeated convergence passes flatten the prose.

If the rewrite fails a final check, repair it once. Do not keep iterating until every sentence shares the same polished register.

## What you must not change

- **Certainty.** Keep the level, not necessarily the words. "Could help reduce" is not "cuts", "typically" is not "always", "the remaining piece" is not "the only big piece". Do not convert association into causation, `may` into `will`, `some` into `most`, or a vendor's claim into narrator fact. But one qualifier is enough to carry it: "can help spot changes before noticeable symptoms appear" can become "can catch changes before you'd notice symptoms".
- **Reasons and conditions.** Do not add an explanation, a cause, an eligibility rule, or a benefit the writer did not state, even an obvious one.
- **Vague into vaguer.** When a claim is vague and you have nothing specific, keep the writer's words or cut the sentence whole. Never swap in a vaguer phrase ("Premium adds more to the app").
- **Who does what.** Keep the actor ("we'll email you" stays with "we" unless the writer is clearly one person).

## The tells, strongest first

### A. Staging: emphasis that adds no information

- **Contrast with a claim nobody made.** "It's not X, it's Y", "not just X but Y", "This isn't about X. It's about Y.", a clipped "no X, no Y" tail. State Y. Keep the contrast only when readers really believe X.
- **Pause-and-point.** "Here's the thing:", "Here's what matters:", "Let me be clear:", "Let's break it down.", the one-line colon reveal ("The best part: it learns."), and a count announced before a list ("This hurts in four ways:", "Three things changed:"). The point should simply be the next sentence.
- **Restating closers.** "The bottom line?", "Key takeaway:", "That's the real win.", "And that's why X is the future.", "What do you think?", "Thoughts?" End on the last concrete thing, or on one line of what the writer concludes.
- **Aphorisms and stacked parallel lines.** "Less clicking. More building." "Automation executes. Agency decides." Budget: at most one crafted, quotable line per piece, and zero is fine. Experienced writers average zero to one even in long posts. Flatten the rest into plain statements that keep the fact.
- **Fragment stacks in prose.** "No setup. No config. Just results." Merge into one sentence with a subject and a verb. Lists are exempt.
- **Invented metaphor labels.** A clever image that names nothing the reader can use ("a comfort blanket", "the operating system for your team"). Say the plain thing.
- **Formula carrying the argument.** Balanced threes, repeated short punchlines, fake questions, and topic-sentence/explanation/zinger paragraphs. Run two tests. The *flatten test*: state the claim without the cadence; if nothing specific remains, the formula was doing the missing reasoning's work. The *relation test*: restate the implied connection using `because`, `although`, `when`, `if`, `which`, or `so`; if that requires inventing a relation, the original only suggested one. Keep an earned contrast, concrete three-item list, short sentence, fragment, or memorable line. Change repeated use or unsupported performance, not the device itself.

### B. Doing the reader's work

Six patterns. Test each sentence by deleting it: if the reader can still recover the meaning, leave it deleted.

1. Defining a word the reader knows ("Revoke the token, which invalidates the session.").
2. Spelling out the implication ("This means that...", "In other words..."), including the trailing -ing rider (", highlighting the team's commitment to...", ", underscoring...", ", reflecting a broader shift").
3. Stating the conclusion the facts already delivered ("So the lesson is...").
4. Pointing ("Notice how...", "As you can see...", "What this shows is...").
5. Telling the reader how to feel ("This is exciting.", "This should worry you.").
6. Narrating transitions ("Now let's look at...", "Moving on to..."). One signpost per major section is fine in a long, sectioned document.

### C. Inflation and generic claims

- **Importance without mechanism.** The sentence claims magnitude instead of showing what happens: pivotal, crucial, transformative, underscores the importance, represents a shift, testament to, broader trend, plays a key role, a pivotal moment, reshaping the landscape, the future looks bright. Test: remove the emphasis. Does the remaining claim name an actor, mechanism, result, or limit? Fix: keep the fact, state the supported mechanism, and let the reader judge its importance. Keep an evaluative word when the same passage supplies the evidence that earns it. `Robust` belongs in an engineering sentence that names the failure handling; it does not belong in "a robust approach" with no mechanism.
- **An adjective with no specific behind it** ("significant", "seamless", "powerful", "robust", "game-changing"). Attach the number, name, or mechanism the source gives, or cut the adjective. Never supply a number the source lacks. Do not add decorative facts to satisfy a density target.
- **Specific-looking vagueness.** An anecdote can have the grammar of an example and the content of an abstraction: "a package once caused a security problem." Ask which package, what happened, and how it was caught. If the source does not contain the answer, use `[TK]` or cut the anecdote. Never fill the gap yourself.
- **Marketing register outside marketing**, and stock AI vocabulary. Lists in `tells.md`. One hit is weak; several together are the tell. Do not replace one watched synonym with another; rewrite the claim or leave it alone.
- **Constructions nobody says out loud.** "The recommended approach is X" becomes "Do X". "Serves as" becomes "is". Nominalizations ("perform an evaluation of") become verbs. Op-ed verbs for sources ("posits", "contends", "asserts") become "says" or "writes". The test: would you say this sentence to a smart friend over coffee? If you'd say something plainer, write that.
- **Vague authority.** "Experts agree", "studies show", "many companies", "observers note", "industry reports suggest". Name who, if the source does. Otherwise preserve explicit uncertainty, ask for the source, scope it ("in our tests"), or cut the claim. A more confident sentence is not automatically a clearer one.
- **Abstract actors.** Decisions do not decide and data does not speak. Name the person, team, system, or documented process when that makes the action clearer. Passive voice remains correct when the actor is unknown, irrelevant, deliberately protected, or less important than the object.

### D. Hedges in the wrong place

People state facts flatly and hedge their opinions. AI text does the reverse, or hedges everything.

- Facts bare: do not add hedges to facts. A qualifier the writer chose ("typically", "about", "could") is part of the fact: keep one, cut the stack around it.
- An opinion gets one marker ("I think", "probably", "in my experience"), never two in a sentence.
- Cut filler hedges everywhere: "arguably", "it's worth noting", "it's important to note", "it could potentially".
- When a claim needs a qualifier, name the case where it does not hold instead of softening it: "For regulated teams, a manual review still wins."
- Never add an absolute ("everyone", "always", "nobody", "the first") the source cannot back.

### E. Rhythm by rule

- **Sentence length.** AI prose clusters in one band, usually 10-20 words. If more than about 70% of sentences sit within five words of the median, vary them, in the right direction. Uniformly long: split one or two and add a short sentence that lands a fact. Uniformly short and choppy, the usual result of removing dashes and fragments: merge into a longer sentence that breathes (25-40 words). The human writers measured ranged from 12% to 66% in that band. A short sentence must carry something; "It works." carries nothing.
- **Openers.** AI starts too many sentences with The, It's, That's, This, and You. Vary them.
- **Triads by reflex.** Keep three items only when there are three things.
- **The shuffle test.** If you could reorder the sentences without losing meaning, the text is a stack of facts, not an argument. Rebuild the spine so each sentence leans on the one before (cause, contrast, example, consequence). Do not sprinkle connectors to fake it.
- **Structural regularity.** Inspect the piece's dominant shape rather than hunting isolated words: sections with identical length and internal order; paragraphs that can trade places without changing the argument; headings doing all the organizing; every example interpreted for the reader; every paragraph ending on a line built to be quoted; a conclusion that recaps or widens into generic optimism. Fix only the dominant problem. Move or combine material, let one section carry more weight, name the relation at a weak join, or stop at the last concrete consequence. Do not introduce a random tangent, unresolved thread, or sentence-length wobble merely to look irregular.
- **Filler transitions at the start of a sentence.** Additionally, Furthermore, Moreover, However, Importantly, Ultimately, In conclusion, That said. Cut or restructure. Plain "But", "So", and "And" are fine when they do work.
- **Synonym cycling.** If two words name the same thing (the tool, the report, the feature), use the same word every time. Readers stop to wonder whether "the platform" and "the solution" are two things.

### F. Punctuation and formatting

- **Em dashes and spaced en dashes:** remove them, unless the writer's own writing uses them. Pick the substitute by context (table in `tells.md`): colon for label-then-description, period for two complete thoughts, parentheses for a real aside, comma for a light pause. **Not a semicolon:** AI edits reroute dashes into semicolons (measured at 2.9 per 1,000 words in AI-edited posts against 0.3-0.4 in the same writer's own prose). And not a colon reveal (section A).
- **Bold-label paragraph starts** ("**Speed.** The new engine..."), bold sprinkled on phrases, emoji bullets, Title Case Headings against house style, and a heading immediately restated by its first sentence: remove.
- **Labels that say nothing.** If every item carries the same label ("Mitigation:", "Benefit:", "Impact:") or the label just repeats its sentence, drop the labels and write the items as sentences. Keep lists and headings where the reader will scan or come back: release notes, specs, steps, options to compare, a reference page. Preserve formatting that supports scanning, accessibility, or the requested medium.
- **Exclamation marks:** at most one, and only where a person would actually exclaim. Never to fake enthusiasm.

### G. Chat residue and surface residue

"Great question!", "Certainly!", "I hope this helps", "Let me know if you'd like...", "Here's a revised version:", "As of my last update". Remove the wrapper, keep the content.

Other surface residue to remove usually: meta narration ("Let's dive in", "In this section", "As we will see", "Without further ado"), empty emphasis ("It is important to note", "At its core", "The real question is"), decorative tails ("highlighting...", "underscoring...", "fostering...", "reflecting..."), and generic endings ("In conclusion", "Ultimately", "Looking ahead", "The future belongs to..."). Treat every list as a search aid, not a ban. Keep quoted text, proper names, terms of art, and an ordinary word used accurately.

## Sound like a person, not a costume

Removing tells is half the job. Plain is not flat. Write the way a competent person in this role writes this genre for this reader, as if saying it to them across a table:

- **Contractions by default** (it's, we're, you'll, don't, that's). Drop them only in formal documents: policies, contracts, formal PRDs.
- **The speaker talks as themselves.** Keep the draft's speaker ("we" stays "we", "I" stays "I"), but let them speak in the first person instead of describing themselves from outside ("The team will review" becomes "We'll review" when the team is writing).
- **Talk to the reader as "you"** wherever the genre addresses a reader.
- **Everyday verbs**: use, help, start, need, fix, send. Not utilize, leverage, facilitate, ensure, enable.
- **Ownership**: "I'll send the tracking number", not "Tracking details will be provided".
- **Warmth where the genre is personal.** A thank-you, an apology, an invitation, a celebration, a note to customers: say the warm thing plainly, once ("Thanks for sticking with us."). One exclamation mark is fine where a person would actually exclaim.
- **Match the room.** Casual where the context is casual (Slack, a community newsletter, a shop's social post); plain and professional where it is formal (PRD, memo, policy). Formal still means plain verbs and complete, natural sentences.
- **Conversational, not colloquial.** Plain spoken English carries the voice. At most one idiom or slangy phrase per paragraph; a cluster of them ("pointy end up", "a natter", "the hard bit") reads as a humanizing pass.

Do not bolt on personality. "Honestly,", "Quick heads-up", "Not bad.", "On a happier note", a rhetorical question to sound chatty, a joke the writer did not make: readers spot an inserted casual pass as fast as they spot AI polish.

## Keep what is already human

- Specific details, unusual word choices, opinions, asides, humor, doubt, mixed feelings, self-corrections, and unusual checkable details. These are what you are protecting. Also protect deliberate repetition of the right ordinary word, trade language, dated references, a slightly surprising phrase that fits the writer, sentence-length variation produced by the thought, and an earned joke, contrast, rhythmic series, or closing beat.
- The reader's working vocabulary: product names and technical terms they would type or search for. Cut jargon that performs expertise; keep terms that let the reader act.
- Genre conventions. A release note can be a list, a PRD can have headers, a support reply can be warm, a letter can have a sign-off.
- If the user gives a writing sample, match its sentence length, punctuation, openings, and register. The sample overrides the rules above.
- **No fake noise.** No planted typos, forced slang, lowercase costume, "lol", or invented "I remember when" stories. Human texture comes from specifics and decisions, not from imitated mistakes. Existing texture can be preserved; invented texture is performance.

## Put craft back

After subtraction, ask:

```txt
Can the reader see, hear, or feel anything where the piece most needs weight?
Does evaluative writing reveal what the writer wants, prefers, fears, or doubts?
Does the syntax express the relationship between thoughts?
Did the edit remove warmth, humor, or a memorable line that the surrounding prose earned?
```

Add only material supported by the source. For a hollow passage, a precise `[TK]` question is a better edit than model-generated color.

## Genre notes

- **Slack, DM, reply in a thread:** the answer or the ask goes first. Cut background the reader already has. One to four sentences is often enough.
- **Cold email:** one specific reason you are writing to this person, from the source, and one ask. No "I hope this finds you well".
- **Social post:** line 1 is the most concrete thing in the post. No engagement-bait closer, no hashtag pile.
- **Release note or product update:** what changed, who it is for, what to do, with the numbers. No "We're thrilled to announce".
- **Landing page:** the concrete outcome and how it happens. Cut empower, unlock, seamless, elevate.
- **Docs, PRDs, policies:** plain and precise; keep the structure; hedge only real uncertainty.

## Final checks (every time)

1. **Fact audit.** Recomposing is where facts slip, so check sentence by sentence against the original draft (when you wrote from the writer's notes, against their notes). Every number, name, date, price, quote, condition, commitment, benefit, and caveat is present, with the same value and the same certainty, and the speaker is unchanged. Watch the strength words: "can help" must not become "will", "might" must not become "would", "little" must not become "no", a proposal must not become a promise, and nothing gains "only", "every", "always", or "guaranteed". Do not make explicit what the draft left implied. Then the other direction: the rewrite adds no fact, example, anecdote, reason, benefit, opinion, or detail the writer did not give, and no new personal experience, preference, source, metric, or causal claim. Warmth and voice are allowed; new content is not.
2. **Mechanical sweep.** Search the final text for em dashes (U+2014), en dashes (U+2013), semicolons, and the lists in `tells.md`. Eyes miss them. If you can run code: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/plainspoken/scripts/lint.py <file>`. Every hit is a prompt to read the passage, not a verdict.
3. **No repeated pattern.** The rewrite does not reproduce the pattern it criticized under different punctuation.
4. **Medium.** The medium still works: procedures scan, warnings remain visible, emails state the ask, and reference material remains retrievable.
5. **Crafted lines:** one or none. The strongest original sentence was left alone unless changing it solved a real problem.
6. **Rhythm:** the band and the openers.
7. **Read it aloud as the writer.** Anything they would not say gets plainer.
8. **Length.** Shorter than a padded input; about the same as an input that was not padded. Never cut a fact, the voice, or the warmth the genre needs to get there. The ending stops on the last useful thought.
9. **Shorter option (run it every time; the writer decides).** Your final text stays as it is. Then cover each paragraph in turn and read the rest: would the reader miss a fact, a commitment, a decision, or the writer's point? A paragraph that fails is a cut candidate. The usual candidates, most common first: an opening that states the point in general terms before the piece shows it (the opening is not protected by being the crafted line: if the examples or the story below make the point better, it is a candidate); lines any similar piece would have (a general moral, a "there's more to do" or "good to pause" close, a second thank-you); a part that says almost the same as another part (keep the stronger one); a second argument or finding that could stand on its own (it can move to a reply, a follow-up, or another piece). Never offer to cut the proof or the stakes: the examples, the numbers, the commitments, or a disclosure that makes the reader trust the piece. Note each candidate with its rough word count and add them up; do the count, do not guess. If the candidates add up to about a quarter of the text or more, offer the shorter option; be bold, a third or half is fine when those parts do not earn their place. Otherwise the answer is "none, it's already tight." Pieces under about 100 words skip this check.

## What to return

The final text. Then `CHANGES:` with at most 5 bullets on what changed, plus any spot where a real specific would help ("A real customer number would make this line land"), and any `[TK]` questions. For a named file, write only the final prose to the file and put the notes in chat.

Then, for any piece over about 100 words, end with one line that starts "Shorter option:" (final check 9). Either the option, offered and never applied: the cuts, roughly how much shorter the piece gets, and any fact a cut would lose and where it could move. Or "none, it's already tight." If the writer asks, write the shorter version in full.
