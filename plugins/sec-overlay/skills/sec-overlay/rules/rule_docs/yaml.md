> Favor precision over recall: only raise a finding when the evidence in the YAML under review is
> confident, and stay silent when the consuming schema or downstream parser is not visible in the
> diff. Adapted from open-code-review (Apache-2.0).

#### Missing Required Keys and Null Value Handling
- A key documented or expected by the consuming schema left absent, or explicitly set to `null`/
  empty, where the consumer treats it as required
- A duplicate key within the same mapping, where a YAML parser silently keeps only the last
  occurrence and discards the first without warning

Do not report in the following cases:
- The key is documented as optional with a stated default, or the consumer already has a fallback
  for a missing or null value
- The duplicate is between unrelated top-level documents in a multi-document stream

#### Anchor and Merge-Key Synchronization Hazards
- Duplicate `<<: *anchor` merge keys on the same mapping resolving in an order that differs across
  YAML implementations, causing environment-dependent value resolution
- An anchor redefined later in the same file, silently changing the value every alias resolves to

Do not report in the following cases:
- A single anchor/alias exists with no merge-key override in the diff
- Anchors are used only for repeated literal values with no override intent visible

#### Injection via Untrusted Interpolation
- An untrusted value flowing into the YAML (from an environment variable, CI input, or another
  file) that a downstream consumer will interpolate into a shell command, SQL query, or template
  without escaping
- A YAML value containing embedded template/expression syntax (e.g. `{{ }}`, `$()`, backticks)
  that a downstream renderer is known to evaluate against attacker-controlled input

Do not report in the following cases:
- The value is a literal constant with no external input path
- The downstream consumer is known, from context in the diff, to treat the field as an opaque
  string with no evaluation

#### Resource Limits and Overbroad Scope Declarations
- A resource-limit or quota field (memory, CPU, timeout, replica count) left unbounded or set to
  an unrealistic maximum where sibling entries in the same file are bounded
- An access-scope or permission-list field set to a wildcard (`*`) or an all-encompassing value
  instead of an enumerated scope

Do not report in the following cases:
- The file has no resource or permission semantics — it is pure data configuration
- The wildcard is the schema's documented default for this field

#### Malformed Structure Hiding Errors
- Indentation or quoting errors that silently change a value's type (unquoted `yes`/`no`/`on`/
  `off` parsed as boolean, an unquoted version number parsed as a float) where the consumer
  expects a string
- A key with a spelling typo that a permissive parser accepts silently, disabling the setting the
  author intended

Do not report in the following cases:
- The value's type is explicitly quoted or documented as intentional
- The typo is already caught by a schema-validation step visible elsewhere in the repository
