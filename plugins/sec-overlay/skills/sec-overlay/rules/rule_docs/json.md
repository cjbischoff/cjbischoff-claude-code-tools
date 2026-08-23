> Favor precision over recall: only raise a finding when the evidence in the JSON
> document is confident, and stay silent when the key's purpose is unclear. Adapted from open-code-review (Apache-2.0).

#### Missing Required Keys and Null Value Misuse
- A key documented or schema-required as present is missing, or a `null` value is
  used where a downstream consumer's contract does not treat `null` as valid
- A key whose value type changes between an object and `null` across the same file's
  sibling entries, signaling inconsistent optionality

Do not report in the following cases:
- The file has no accompanying schema/contract establishing the key as required
- `null` is the documented sentinel for "unset" in this config's consumer

#### Concurrency and Non-Deterministic Key Ordering Assumptions
JSON objects have no threads, but key order is not guaranteed by the spec:
- Application logic that depends on JSON object key iteration order for correctness
  (e.g. "first key wins") when no schema or library guarantees ordering
- Do not report in the following cases:
  - The consumer explicitly documents and relies on an ordered-map parser
  - No evidence the file is consumed by order-sensitive logic

#### Hardcoded Secrets and Injection-Prone Values
- A value that is a plaintext password, API key, access token, or private key
  material stored directly in the JSON file
- A value later interpolated into a shell command, SQL query, or file path by a
  known consumer, with no indication of escaping/validation at that boundary

Do not report in the following cases:
- The value is clearly a placeholder/example (e.g. `"CHANGE_ME"`, `"xxx"`) in a
  template or sample config, not a real credential
- The consuming code path is not visible and the key name gives no injection signal

#### Resource Exhaustion: Unbounded Collections in Config
- An array or object key documented to bound a resource (page size, retry count,
  connection pool, timeout) set to an unbounded or extremely large value with no
  corresponding safeguard elsewhere
- Do not report in the following cases:
  - No evidence the value maps to a resource limit as opposed to arbitrary data
  - The value is within the range documented for the consuming system

#### Malformed Structure Masking Errors
- Duplicate keys within the same object, where the later value silently overrides
  the earlier one and both look intentional
- A value's type silently changed (e.g. numeric string `"3"` vs. number `3`) in a
  way that a loosely-typed consumer would misinterpret as valid instead of failing

Do not report in the following cases:
- The JSON parser used by the consumer already rejects duplicate keys / type
  mismatches, and that behavior is documented
- The change is a like-for-like edit of an existing value with no type change
