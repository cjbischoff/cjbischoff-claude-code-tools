#!/usr/bin/env python3
"""Locate writing habits in a draft. Diagnostic only, stdlib only.

Merged from two sources, with changes:

* clarity (MIT, Addy Osmani): the size, cadence, density, high-signal cluster, and
  look-here measurements come from clarity's ``prose_stats.py``. The Markdown
  stripping comes from clarity's ``strip_markdown.py``. See ``NOTICE.md``.
* work-humanizer ``check.py``: the ``sweep`` group (dashes, semicolons, stock words,
  filler transitions, pause-and-point lines, closers, hedges, bold-label starts,
  exclamation marks, the sentence-length band, and the opener share).

This script deliberately reports no composite score, no verdict, and no risk number.
Clarity's reason, kept here: a stylometric composite run over texts with classifier
verdicts attached came out inverted. The genuinely human control scored "riskiest" in
the original exploratory corpus. The measurements are diagnostics, not targets. A
single number invites optimizing toward the machine register, so there is not one here.

Read the output as a map of where to look. Every hit is a hypothesis. Open the
paragraph and decide in context. Lexicons drift with language and model generations:
an absence is not a pass, and a match is not a defect without context.

The word lists live in ``references/tells.md`` for human readers and in the constants
below. A test (``tests/test_lint.py``) fails when the two disagree.

Usage:
    python3 lint.py draft.md              # human-readable report
    python3 lint.py draft.md --json       # machine-readable report
    python3 lint.py draft.md --raw        # skip Markdown stripping
    cat draft.md | python3 lint.py -      # read standard input

Exit codes: 0 on success, 2 when the file is missing or unreadable (or on bad usage).
"""

from __future__ import annotations

import argparse
import io
import json
import re
import statistics
import sys

# ---------------------------------------------------------------- lexicons
# Mirrors references/tells.md. Entries are lowercase. Time-dated search lexicons:
# an absence is not a pass, and a match is not a defect without context.


def _csv(entries: str) -> tuple[str, ...]:
    """Split a comma-separated lexicon string into a tuple of entries.

    Args:
        entries: Entries separated by commas, as written in ``tells.md``.

    Returns:
        The stripped, non-empty entries in their original order.

    Example:
        >>> _csv("delve, bolster")
        ('delve', 'bolster')
    """
    return tuple(e.strip() for e in entries.split(",") if e.strip())


AI_WORDS = _csv(
    "delve, bolster, illuminate, elucidate, transcend, intertwine, espouse, exemplify, "
    "underpin, underscore, underscoring, tapestry, synergy, beacon, interplay, intricacies, "
    "intricate, symphony, kaleidoscope, myriad, plethora, advancements, vibrant, meticulous, "
    "cutting-edge, game-changing, unparalleled, commendable, indelible, poignant, tireless, "
    "unwavering, unyielding, timeless, ever-evolving, showcase, showcasing, leverage, "
    "leveraging, foster, fostering, garner, multifaceted, utilize, utilizing, facilitate, "
    "cornerstone"
)

AI_PHRASES = _csv(
    "shed light on, grapple with, stands as a testament, testament to, rich tapestry, "
    "navigate the complexities, navigating the, paving the way, look no further, that being "
    "said, ever-changing landscape, landscape of, a myriad of, plays a crucial role, plays a "
    "vital role, plays a key role, the world of, deep dive, double down, circle back, lean "
    "into"
)

MARKETING = _csv(
    "empower, unlock, elevate, seamless, streamline, revolutioniz, supercharge, next-level, "
    "best-in-class, world-class, game-changer, harness the power, take it to the next level, "
    "thrilled to announce, excited to announce"
)

TRANSITIONS = _csv(
    "additionally, furthermore, moreover, however, importantly, critically, notably, "
    "ultimately, therefore, in fact, lastly, that said, needless to say, in other words, as "
    "we can see, consequently, thus, indeed, similarly, conversely, nevertheless, "
    "nonetheless, accordingly, hence, overall, instead, meanwhile, essentially"
)

POINTING = _csv(
    "here's the thing, here's what, here's why, here's the kicker, let me be clear, let me "
    "explain, let's break, let's dive, let's explore, what nobody tells you, the real story "
    "is, one thing trips people up, the truth is, honestly?, the best part:, the secret:, "
    "notice how, as you can see, this means that, in today's, in the realm of, when it comes "
    "to, at its core, in a world where, the reality is, without further ado, the "
    "uncomfortable truth, make no mistake"
)

CLOSERS = _csv(
    "the bottom line, key takeaway, tl;dr, that's the real win, that's the power of, and "
    "that's why, the future is, what do you think?, thoughts?, agree?, let that sink in, read "
    "that again, in conclusion, in summary, to sum up, to summarize, in short, all in all, in "
    "essence, taken together, at the end of the day"
)

FILLER_HEDGES = _csv(
    "arguably, it's worth noting, it is worth noting, it's important to note, it is important "
    "to note, could potentially, it may be possible that, to some extent, in many ways, i "
    "think maybe"
)

ATTRIBUTION = _csv("posits, contends, asserts, maintains that, concedes, argues that")

CHATBOT = _csv(
    "i hope this helps, i hope this email finds you well, let me know if, would you like me "
    "to, great question, you're absolutely right, certainly!, of course!, absolutely!, as of "
    "my last, based on available information, feel free to reach out, here's a revised "
    "version, as an ai, happy to help"
)

HEDGES = _csv(
    "may, might, could, perhaps, possibly, likely, generally, typically, often, usually, "
    "tends, tend, suggests, suggest, appears, appear, seems, seem, arguably, relatively, "
    "somewhat, potentially, presumably, largely, broadly, commonly, roughly, sometimes, "
    "mostly, probably, fairly, can, would, maybe, basically, quite, pretty, really, almost, "
    "occasionally, apparently, supposedly, unclear, unsure"
)

HEDGE_PHRASES = _csv(
    "kind of, sort of, a bit, i think, i guess, i suspect, more or less, pretty much, at "
    "least in, in practice, or so, if anything, for the most part, as far as i"
)

BOOSTERS = _csv(
    "crucial, crucially, essential, essentially, vital, key, significant, significantly, "
    "robust, powerful, remarkable, remarkably, notable, notably, critical, critically, "
    "profound, profoundly, compelling, paramount, pivotal, important, importantly, "
    "substantial, substantially, transformative, groundbreaking, invaluable, seamless, "
    "seamlessly"
)

PARTICIPIAL_HEADS = _csv(
    "building, drawing, having, given, considering, looking, leveraging, combining, "
    "reflecting, highlighting, underscoring, starting, moving, taking, using, adding, "
    "focusing, recognizing, acknowledging, understanding, beginning, turning, returning, "
    "stepping, bearing, armed, faced, based"
)

COPULA_PHRASES = _csv("serves as, stands as, represents, marks a, features a, boasts, offers a")

OPENER_WORDS = _csv("the, it's, that's, this, you, it, these")

# Name -> entries, for the sync test. One entry per `Entries:` line in tells.md.
LEXICONS = {
    "ai_words": AI_WORDS,
    "ai_phrases": AI_PHRASES,
    "marketing": MARKETING,
    "transitions": TRANSITIONS,
    "pause_and_point": POINTING,
    "closers": CLOSERS,
    "filler_hedges": FILLER_HEDGES,
    "attribution": ATTRIBUTION,
    "chatbot": CHATBOT,
    "hedges": HEDGES,
    "hedge_phrases": HEDGE_PHRASES,
    "boosters": BOOSTERS,
    "participial_heads": PARTICIPIAL_HEADS,
    "copula": COPULA_PHRASES,
    "opener_words": OPENER_WORDS,
}

HEDGE_WORDS = frozenset(HEDGES)
BOOSTER_WORDS = frozenset(BOOSTERS)

CONTRASTIVE = [
    re.compile(r"\brather than\b", re.I),
    re.compile(r"\bnot simply\b", re.I),
    re.compile(r"\bnot merely\b", re.I),
    re.compile(r"\bnot necessarily\b", re.I),
    re.compile(r"\bnot solely\b", re.I),
    re.compile(r"\bas opposed to\b", re.I),
    re.compile(r"\beven as\b", re.I),
    re.compile(r"\bnot just\b[^.?!]{0,60}\bbut\b", re.I),
    re.compile(r"\bnot only\b[^.?!]{0,60}\bbut\b", re.I),
    re.compile(r"\bisn'?t\b[^.?!]{0,40}\bit'?s\b", re.I),
    re.compile(r"\bis not\b[^.?!]{0,40}\bit is\b", re.I),
    re.compile(r"\bthe question is ?n'?t\b", re.I),
    re.compile(r";\s+the\s+[^.?!;]{1,45}\bremains?\b", re.I),
    # work-humanizer: "It's not about X. It's Y."
    re.compile(r"\bit'?s not (?:just )?(?:about )?[^.]{1,40}[,.;] it'?s\b", re.I),
]

COPULA = re.compile(r"\b(" + "|".join(map(re.escape, COPULA_PHRASES)) + r")\b", re.I)

FALSE_AGENCY = re.compile(
    r"\b(the (decision|culture|conversation|complaint|data|market|industry|"
    r"technology|process|architecture)\s+"
    r"(emerges?|shifts?|moves?|tells?|rewards?|demands?|becomes?|drives?|"
    r"speaks?|listens?|decides?|wants?))\b",
    re.I,
)

PARTICIPIAL = re.compile(r"^\s*(" + "|".join(PARTICIPIAL_HEADS) + r")\b[^,\n]{2,60},", re.I)

TRIAD = re.compile(
    r"\b([A-Za-z][\w'-]*(?:[ \t]+[\w'-]+){0,2}),[ \t]+"
    r"([A-Za-z][\w'-]*(?:[ \t]+[\w'-]+){0,2}),[ \t]+"
    r"(?:and|or)[ \t]+([A-Za-z][\w'-]*(?:[ \t]+[\w'-]+){0,2})\b"
)

# work-humanizer: a short "Label: lowercase reveal" line, such as "The best part: it works".
REVEAL_LABEL = re.compile(r"^[A-Z][^.:!?\n]{2,40}: [a-z].*$", re.M)
BOLD_LABEL = re.compile(r"^\s*\*\*[^*]{1,60}(?:\*\*[.:]|[.:]\*\*)", re.M)

SENT_RE = re.compile(r'[^.!?]*[.!?]+["\')\]]?|\S[^.!?]*$', re.S)
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
DASH_RE = re.compile(r"—|–|(?<=\s)--(?=\s)|(?<=\s)-(?=\s)")
NUM_RE = re.compile(r"\b\d[\d,.]*\b|\b\d+%")
PROPER_RE = re.compile(r"\b[A-Z][a-zA-Z0-9]*\b")
QUOTE_RE = re.compile(r'"[^"]{4,}"|“[^”]{4,}”')

BODY_MIN_WORDS = 8
BAND_SHARE = 0.7  # share of sentences within 5 words of the median that counts as uniform
BAND_WIDTH = 5
OPENER_SHARE = 0.4

COMMON_CAPS = {
    "The", "A", "An", "I", "It", "This", "That", "These", "Those", "But", "And",
    "Or", "So", "If", "When", "While", "You", "We", "They", "He", "She", "There",
    "What", "Why", "How", "Where", "Who", "Because", "Although", "Once", "For",
    "In", "On", "At", "To", "By", "As", "Not", "No", "Yes", "Every", "Most",
    "Some", "Each", "One", "Two", "Three", "After", "Before", "Then", "Now",
    "Here", "His", "Her", "Their", "Our", "Its", "My", "Do", "Does", "Did",
}  # fmt: skip


# ---------------------------------------------------------------- markdown


def _drop_comments(text: str) -> str:
    """Remove closed HTML comments in linear time.

    A regex such as ``<!--.*?-->`` rescans to the end of the text from every
    unclosed ``<!--``, which is quadratic. An unclosed comment stays in the text.

    Args:
        text: Markdown source.

    Returns:
        The text without its closed ``<!-- ... -->`` comments.

    Example:
        >>> _drop_comments("a<!-- x -->b<!-- open")
        'ab<!-- open'
    """
    out, i = [], 0
    while (j := text.find("<!--", i)) != -1:
        k = text.find("-->", j + 4)
        if k == -1:
            break
        out.append(text[i:j])
        i = k + 3
    out.append(text[i:])
    return "".join(out)


def drop_code(text: str) -> str:
    """Remove the parts of a Markdown file that are not prose and not markup labels.

    Removes YAML frontmatter, HTML comments, fenced code (backticks and tildes), and
    indented code blocks. Emphasis marks stay, so bold-label starts remain countable.

    Args:
        text: Markdown source.

    Returns:
        The source without frontmatter, comments, and code blocks.

    Example:
        >>> drop_code("Hi.\\n\\n```\\ncode\\n```\\n")
        'Hi.\\n\\n\\n'
    """
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = _drop_comments(text)
    text = re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)
    text = re.sub(r"^~~~.*?^~~~", "", text, flags=re.S | re.M)
    return re.sub(r"^(?: {4}|\t).*$", "", text, flags=re.M)


def strip(text: str) -> str:
    """Reduce a Markdown draft to the prose a reader reads.

    Removes frontmatter, comments, fenced and inline code, images, URLs, tables,
    rules, and heading, list, quote, and emphasis marks. Link text stays and the URL
    goes. Clarity's version kept inline-code text. This one drops it, because code
    spans are not prose.

    Args:
        text: Markdown source.

    Returns:
        Plain prose ending in one newline.

    Example:
        >>> strip("# Title\\n\\nUse `code` and **bold**.\\n")
        'Title\\n\\nUse  and bold.\\n'
    """
    text = drop_code(text)
    text = re.sub(r"!\[[^\[\]]*\]\([^()]*\)", "", text)  # images before links
    text = re.sub(r"\[([^\[\]]*)\]\([^()]*\)", r"\1", text)
    text = re.sub(r"\[([^\[\]]*)\]\[[^\[\]]*\]", r"\1", text)
    text = re.sub(r"^\s*\[[^\]]+\]:\s+\S.*$", "", text, flags=re.M)
    text = re.sub(r"`+[^`]*`+", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^\s*\|.*$", "", text, flags=re.M)
    text = re.sub(r"^\s*(?:[-*_]\s*){3,}$", "", text, flags=re.M)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.M)
    text = re.sub(r"^\s{0,3}(?:[-*+]|\d+\.)\s+", "", text, flags=re.M)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"(?<![\w_])_([^_]+)_(?![\w_])", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    text = re.sub(r"</?[a-zA-Z][^<>]*>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# ---------------------------------------------------------------- helpers


def sentences(text: str) -> list[str]:
    """Split prose into sentences.

    Args:
        text: Plain prose.

    Returns:
        Non-empty, stripped sentences in order.

    Example:
        >>> sentences("One. Two!")
        ['One.', 'Two!']
    """
    return [m.group().strip() for m in SENT_RE.finditer(text) if m.group().strip()]


def paragraphs(text: str) -> list[str]:
    """Split prose into paragraphs at blank lines.

    Args:
        text: Plain prose.

    Returns:
        Non-empty, stripped paragraphs in order.

    Example:
        >>> paragraphs("a\\n\\nb")
        ['a', 'b']
    """
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def cv(values: list[int]) -> float:
    """Return the coefficient of variation of the positive values.

    Args:
        values: Counts such as sentence lengths. Zeros are ignored.

    Returns:
        Population standard deviation over the mean, or 0.0 for fewer than two values.

    Example:
        >>> cv([10, 10, 10])
        0.0
    """
    vals = [v for v in values if v > 0]
    if len(vals) < 2:
        return 0.0
    return statistics.pstdev(vals) / statistics.mean(vals)


def phrase_hits(text: str, entries: tuple[str, ...], prefix: bool = False) -> list[str]:
    """List the lexicon entries that occur in the text.

    Matching is case-insensitive and respects word edges. A curly apostrophe counts as a
    straight one.

    Args:
        text: Text to search.
        entries: Lowercase lexicon entries.
        prefix: When true, an entry matches from the start of a word, so a stem such as
            ``revolutioniz`` covers its inflections. When false, the entry must end at
            a word edge.

    Returns:
        The entries found, in lexicon order, without repeats.

    Example:
        >>> phrase_hits("We delve into it.", ("delve", "bolster"))
        ['delve']
    """
    text = text.replace("’", "'")
    tail = "" if prefix else r"(?!\w)"
    return [e for e in entries if re.search(r"(?<!\w)" + re.escape(e) + tail, text, re.I)]


def regex_hits(text: str, regexes: list[re.Pattern[str]]) -> list[str]:
    """Collect every match of every pattern.

    Args:
        text: Text to search.
        regexes: Compiled patterns.

    Returns:
        The matched strings, stripped, in pattern order.

    Example:
        >>> regex_hits("not just fast but cheap", [re.compile(r"not just \\w+ but")])
        ['not just fast but']
    """
    return [m.group().strip() for rx in regexes for m in rx.finditer(text)]


def starts_with_transition(sentence: str) -> str | None:
    """Return the filler transition that opens a sentence, if any.

    Args:
        sentence: One sentence.

    Returns:
        The lexicon entry the sentence starts with, or None.

    Example:
        >>> starts_with_transition("However, it works.")
        'however'
    """
    for entry in TRANSITIONS:
        if re.match(r"\W*" + re.escape(entry) + r"(?!\w)", sentence, re.I):
            return entry
    return None


def count_anchors(text: str, sents: list[str]) -> int:
    """Count numbers, quoted strings, and proper nouns that do not open a sentence.

    Args:
        text: Plain prose.
        sents: The sentences of the same prose.

    Returns:
        The anchor count. Concrete anchors suggest specific writing.

    Example:
        >>> count_anchors("We met Dana in 2024.", ["We met Dana in 2024."])
        2
    """
    anchors = len(NUM_RE.findall(text)) + len(QUOTE_RE.findall(text))
    for s in sents:
        for w in s.split()[1:]:
            token = w.strip(".,;:!?()[]\"'")
            if not token or token in COMMON_CAPS:
                continue
            if PROPER_RE.fullmatch(token) and not token.isupper() and len(token) > 1:
                anchors += 1
            elif token.isupper() and len(token) > 1 and token.isalpha():
                anchors += 1
    return anchors


# ---------------------------------------------------------------- sweep


def sweep(text: str, label_source: str) -> dict:
    """Run work-humanizer's mechanical sweep.

    Only checks with hits appear in the result, so a clean text gives an empty dict.

    Args:
        text: Plain prose to check.
        label_source: Text to scan for bold-label starts. It keeps Markdown emphasis
            marks, which ``text`` may have lost.

    Returns:
        A dict of the checks that found something. Lists hold lexicon entries, ints hold
        counts, and ``uniform_band`` and ``opener_share`` hold small detail dicts.

    Example:
        >>> sweep("We delve in!", "We delve in!")
        {'ai_words': ['delve'], 'exclamation_marks': 1}
    """
    text = text.replace("’", "'")
    sents = sentences(text)
    out: dict = {}

    def put(key: str, value) -> None:
        if value:
            out[key] = value

    put("dashes", text.count("—") + len(re.findall(r" – | -- ", text)))
    put("semicolons", text.count(";"))
    put("ai_words", phrase_hits(text, AI_WORDS, prefix=True))
    put("ai_phrases", phrase_hits(text, AI_PHRASES))
    put("marketing_words", phrase_hits(text, MARKETING, prefix=True))
    put("filler_transitions", sorted({t for s in sents if (t := starts_with_transition(s))}))
    put(
        "pause_and_point",
        phrase_hits(text, POINTING) + [m.group()[:50] for m in REVEAL_LABEL.finditer(text)],
    )
    put("closers", phrase_hits(text, CLOSERS))
    put("filler_hedges", phrase_hits(text, FILLER_HEDGES))
    put("attribution_verbs", phrase_hits(text, ATTRIBUTION))
    put("bold_label_starts", len(BOLD_LABEL.findall(label_source)))
    put("exclamation_marks", text.count("!"))

    spoken = [s for s in sents if len(s.split()) >= 2]
    if len(spoken) >= 4:
        lens = [len(s.split()) for s in spoken]
        median, mean = statistics.median(lens), statistics.mean(lens)
        share = sum(1 for n in lens if abs(n - median) <= BAND_WIDTH) / len(lens)
        if share >= BAND_SHARE:
            out["uniform_band"] = {
                "sentences": len(lens),
                "mean_words": round(mean, 1),
                "share_within_5_of_median": round(share, 2),
                "note": "merge short ones" if mean < 11 else "vary the length",
            }
        starts = [s.split()[0].lower().strip("\"'") for s in spoken]
        opener = sum(1 for w in starts if w in OPENER_WORDS) / len(starts)
        if opener >= OPENER_SHARE:
            out["opener_share"] = {
                "share": round(opener, 2),
                "note": "sentences that start with The/It/This/That/You/These",
            }
    return out


# ---------------------------------------------------------------- analysis


def analyze(text: str, raw: bool = False) -> dict:
    """Measure a draft.

    Args:
        text: The draft as written, usually Markdown.
        raw: When true, skip Markdown stripping and measure the text as given.

    Returns:
        A dict with the groups ``size``, ``cadence``, ``density``,
        ``high_signal_clusters``, ``look_here``, and ``sweep``. There is no score, no
        verdict, and no risk key.

    Example:
        >>> sorted(analyze("A short note.")["size"])
        ['paragraphs', 'sentences', 'words']
    """
    body = (text if raw else strip(text)).replace("’", "'")
    label_source = text if raw else drop_code(text)
    sents = sentences(body)
    paras = paragraphs(body)
    words = WORD_RE.findall(body)
    n_words = len(words) or 1

    sent_lens = [len(WORD_RE.findall(s)) for s in sents]
    body_lens = [n for n in sent_lens if n >= BODY_MIN_WORDS]
    short_lens = [n for n in sent_lens if n < BODY_MIN_WORDS]

    lowered = [w.lower() for w in words]
    low_text = body.lower()
    n_hedge = sum(1 for w in lowered if w in HEDGE_WORDS)
    n_hedge += sum(low_text.count(p) for p in HEDGE_PHRASES)
    n_boost = sum(1 for w in lowered if w in BOOSTER_WORDS)

    co_occur = [
        s[:110]
        for s in sents
        if {w.lower() for w in WORD_RE.findall(s)} & HEDGE_WORDS
        and {w.lower() for w in WORD_RE.findall(s)} & BOOSTER_WORDS
    ]
    signpost_openers = [s[:90] for s in sents if starts_with_transition(s)]
    participial_openers = [s[:90] for s in sents if PARTICIPIAL.match(s)]
    dash_clusters = [s[:110] for s in sents if len(DASH_RE.findall(s)) >= 2]
    anchors = count_anchors(body, sents)

    long_sents = sorted(((len(WORD_RE.findall(s)), s) for s in sents), key=lambda x: -x[0])

    return {
        "size": {"words": len(words), "sentences": len(sents), "paragraphs": len(paras)},
        "cadence": {
            "body_sentence_cv": round(cv(body_lens), 3),
            "all_sentence_cv": round(cv(sent_lens), 3),
            "short_line_share": round(len(short_lens) / len(sent_lens), 3) if sent_lens else 0.0,
            "paragraph_word_cv": round(cv([len(WORD_RE.findall(p)) for p in paras]), 3),
            "mean_body_sentence_words": round(statistics.mean(body_lens), 1) if body_lens else 0.0,
        },
        "density": {
            "hedge_booster_per_100": round((n_hedge + n_boost) / n_words * 100, 2),
            "hedge_per_100": round(n_hedge / n_words * 100, 2),
            "booster_per_100": round(n_boost / n_words * 100, 2),
            "anchors_per_100": round(anchors / n_words * 100, 2),
            "signpost_opener_share": round(len(signpost_openers) / len(sents), 3) if sents else 0.0,
        },
        "high_signal_clusters": {
            "hedge_booster_same_sentence": co_occur,
            "participial_openers": participial_openers,
            "contrastive_pivots": regex_hits(body, CONTRASTIVE),
        },
        "look_here": {
            "triads": [" / ".join(m) for m in TRIAD.findall(body)][:25],
            "copula_displacement": [m.group() for m in COPULA.finditer(body)],
            "false_agency": [m.group() for m in FALSE_AGENCY.finditer(body)],
            "signpost_openers": signpost_openers[:25],
            "multi_dash_sentences": dash_clusters,
            "overloaded_sentences": [f"({n}w) {s[:96]}" for n, s in long_sents if n > 40],
            "chatbot_residue": phrase_hits(body, CHATBOT),
        },
        "sweep": sweep(body, label_source),
    }


# ---------------------------------------------------------------- report


def _section(title: str, group: dict) -> list[str]:
    """Format one group of hits for the human report."""
    lines = ["", title]
    shown = False
    for key, items in group.items():
        if not items:
            continue
        shown = True
        if isinstance(items, dict):
            lines.append(f"  {key}")
            lines += [f"      {k}: {v}" for k, v in items.items()]
        elif isinstance(items, int):
            lines.append(f"  {key}: {items}")
        else:
            lines.append(f"  {key} ({len(items)})")
            lines += [f"      {item}" for item in items[:8]]
            if len(items) > 8:
                lines.append(f"      ... {len(items) - 8} more")
    if not shown:
        lines.append("  (no hits)")
    return lines


def report(stats: dict) -> str:
    """Format the analysis as a human-readable report.

    Args:
        stats: The dict from :func:`analyze`.

    Returns:
        A multi-line report. It ends with the reminder that counts do not grade prose.

    Example:
        >>> "No composite score" in report(analyze("A short note."))
        True
    """
    size, cad, den = stats["size"], stats["cadence"], stats["density"]
    lines = [
        f"{size['words']} words, {size['sentences']} sentences, {size['paragraphs']} paragraphs"
    ]
    if size["words"] < 400:
        lines.append(
            "  note: under 400 words. Cadence and density figures are unstable at this "
            "length, and so is any judgement made from a short excerpt."
        )
    lines += ["", "MEASUREMENTS (descriptive, not targets)"]
    lines += [
        f"  body_sentence_cv           {cad['body_sentence_cv']}",
        f"  short_line_share           {cad['short_line_share']}",
        f"  hedge_per_100              {den['hedge_per_100']}",
        f"  booster_per_100            {den['booster_per_100']}",
        f"  anchors_per_100            {den['anchors_per_100']}",
        f"  signpost_opener_share      {den['signpost_opener_share']}",
        "  Compare versions of the same piece. Do not compare a draft to a universal norm.",
    ]
    if cad["short_line_share"] > 0.15:
        lines += [
            "  note: many lines are under 8 words. If those are headings, list items, or",
            "        section breaks, read body_sentence_cv and ignore the short-line share.",
        ]
    lines += _section("HIGH-SIGNAL CLUSTERS (inspect in context)", stats["high_signal_clusters"])
    lines += _section("LOOK HERE (hypotheses, not verdicts)", stats["look_here"])
    lines += _section("SWEEP (mechanical checks, read each hit in context)", stats["sweep"])
    lines += [
        "",
        "No composite score, by design. Counts locate passages. They do not grade prose.",
        "These numbers find habits. They do not tell you whether the piece is good,",
        "and they cannot tell you whether it says anything. Read the passage to decide.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- cli


def read_input(path: str) -> str:
    """Read the draft from a file or from standard input.

    Args:
        path: A file path, or ``-`` for standard input.

    Returns:
        The text, decoded as UTF-8.

    Raises:
        OSError: If the file is missing or unreadable.
        UnicodeDecodeError: If the file is not valid UTF-8.

    Example:
        >>> read_input("draft.md")  # doctest: +SKIP
        'First line.\\n'
    """
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface.

    Args:
        argv: Arguments after the program name. None means ``sys.argv[1:]``.

    Returns:
        The exit code: 0 on success, 2 when the input cannot be read.

    Example:
        >>> main(["missing-file.md"])  # doctest: +SKIP
        2
    """
    parser = argparse.ArgumentParser(description="Locate writing habits in a draft.")
    parser.add_argument("path", help="draft file, or - for standard input")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    parser.add_argument("--raw", action="store_true", help="skip Markdown stripping")
    args = parser.parse_args(argv)

    for stream in (sys.stdin, sys.stdout):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    try:
        text = read_input(args.path)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"lint.py: cannot read {args.path}: {exc}", file=sys.stderr)
        return 2

    stats = analyze(text, raw=args.raw)
    print(json.dumps(stats, indent=2, ensure_ascii=False) if args.json else report(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
