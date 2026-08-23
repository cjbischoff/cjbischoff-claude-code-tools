> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Null and Empty Translation
- `msgstr` missing entirely for a non-fuzzy entry, or an empty `msgstr` a consumer
  will render as blank text in production UI
- Orphaned `msgstr` without a preceding `msgid`, or a duplicate `msgid` whose entries
  conflict

Do not report in the following cases:
- The entry is marked `fuzzy` or clearly a work-in-progress draft
- The empty translation is intentional for a key the application overrides at runtime

#### Concurrency
- Not applicable: a `.po` catalog is a static data file with no concurrent-execution
  semantics of its own

Do not report in the following cases:
- Any `.po` file content — catalog parsing/loading concurrency is a consumer concern,
  not a property of the file
- N/A

#### Format-String Injection and Placeholder Mismatch
- Format placeholders (`%s`, `%d`, `%(name)s`) present in the `msgid` but missing,
  reordered without positional markers, or changed in type in the `msgstr` — can crash
  or corrupt output at format time
- Brace-style placeholders (`{0}`, `{name}`) whose count or names differ between
  `msgid` and `msgstr`, or unescaped markup injected into an `msgstr` a consumer
  renders as raw HTML

Do not report in the following cases:
- Reordering correctly expressed with explicit positional markers (`%1$s`)
- Subjective wording, tone, or regional variants when the meaning is preserved

#### Resource Management
- Not applicable: catalog entries hold no file handles, sockets, or acquired resources

Do not report in the following cases:
- Any `.po` file content — no resource acquisition occurs in this file type
- N/A

#### Error Handling
- Not applicable beyond structural validity: a malformed entry (unbalanced quotes,
  broken escape sequence) fails at load time rather than being "swallowed"

Do not report in the following cases:
- Any `.po` file content with no broken quote/escape sequence present
- N/A
