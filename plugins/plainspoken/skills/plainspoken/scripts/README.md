# scripts/

`lint.py` is the mechanical check behind the `lint` mode. It is stdlib only and needs Python 3.10 or later.

## Purpose

It finds places in a draft where a person should look. It does not edit, grade, or judge. Every hit is a hypothesis. Read the passage and decide in context.

## Usage

```bash
python3 lint.py draft.md              # human-readable report
python3 lint.py draft.md --json       # machine-readable report
python3 lint.py draft.md --raw        # skip Markdown stripping
cat draft.md | python3 lint.py -      # read standard input
```

By default the script strips Markdown first. Frontmatter, fenced and inline code, tables, URLs, and HTML comments do not count. `--raw` measures the text as given.

Exit code 0 means success. Exit code 2 means the file is missing or unreadable, or the usage is wrong. A message goes to stderr.

## JSON groups

| Group | Holds | Source |
|-------|-------|--------|
| `size` | Words, sentences, paragraphs | clarity |
| `cadence` | Sentence-length spread, short-line share, paragraph spread | clarity |
| `density` | Hedges, boosters, anchors per 100 words, signpost opener share | clarity |
| `high_signal_clusters` | Hedge and booster in one sentence, participial openers, contrastive pivots | clarity, plus one contrast pattern from work-humanizer |
| `look_here` | Triads, copula displacement, false agency, signpost openers, multi-dash sentences, overloaded sentences, chat residue | clarity |
| `sweep` | Dashes, semicolons, stock AI words and phrases, marketing words, filler transitions at sentence start, pause-and-point lines, closers, filler hedges, attribution verbs, bold-label starts, exclamation marks, the sentence-length band, the opener share | work-humanizer |

`sweep` lists only checks that found something. A clean draft gives `"sweep": {}`.

## No score

The script reports no composite score, no verdict, and no risk number, by design. Clarity measured why. A stylometric composite run over texts with classifier verdicts attached came out inverted: the genuinely human control scored "riskiest" in the original exploratory corpus. A single number invites optimizing toward the machine register. Counts locate passages. They do not grade prose.

## Word lists

The lists in `lint.py` mirror `../references/tells.md`. A test (`../../../tests/test_lint.py`) fails when an entry is in `tells.md` but not in the script. Change both in the same commit.

## Attribution

The measurements and the Markdown stripping come from clarity's `prose_stats.py` and `strip_markdown.py` (MIT, Addy Osmani). The `sweep` group comes from work-humanizer's `check.py` (MIT, Pawel Huryn). See `../../../NOTICE.md`.

## Regular expressions

Every pattern runs in linear time on hostile input: no nested quantifiers, and no pattern that rescans to the end of the text from each unclosed `<!--`, `[`, `(`, or `<`. HTML comments are removed with `str.find`, not a regex. `tests/test_lint.py` enforces a time limit.
