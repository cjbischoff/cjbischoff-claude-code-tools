> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Null and Malformed Header Values
- Missing or malformed `Content-Type` charset header, or a `Plural-Forms` header whose
  `nplurals`/`plural` expression does not parse as a valid C-style ternary
- A non-empty `msgstr` in a template entry — usually a translation accidentally
  committed into the template

Do not report in the following cases:
- Missing optional metadata fields (`Project-Id-Version`, `Report-Msgid-Bugs-To`)
- An empty `msgstr` — every `msgstr` in a `.pot` template is expected to be empty

#### Concurrency
- Not applicable: a `.pot` template is a static data file with no concurrent-execution
  semantics of its own

Do not report in the following cases:
- Any `.pot` file content — catalog parsing/loading concurrency is a consumer concern
- N/A

#### Format-String Injection and Placeholder Consistency
- Format placeholders (`%s`, `%d`, `%(name)s`) present in `msgid` but missing,
  reordered without positional markers, or changed in type in `msgid_plural`
- `msgid_plural` present with no `Plural-Forms` header declared, or a singular-only
  entry whose text embeds a count placeholder, indicating a forgotten plural form

Do not report in the following cases:
- Reordering correctly expressed with explicit positional markers (`%1$s`)
- A `plural` expression whose reachable form count matches the declared `nplurals`

#### Resource Management
- Not applicable: template entries hold no file handles, sockets, or acquired
  resources

Do not report in the following cases:
- Any `.pot` file content — no resource acquisition occurs in this file type
- N/A

#### Error Handling
- Not applicable beyond structural validity: a malformed entry (unbalanced quotes,
  broken escape sequence, orphaned `msgid_plural`) fails at load time rather than
  being "swallowed"

Do not report in the following cases:
- Any `.pot` file content with no broken quote/escape sequence or orphaned entry
- N/A
