> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Null Parameter Handling
- A `<if test="paramName != null">` dynamic-SQL guard missing for a parameter that can
  legitimately be null, causing the wrong branch of the query to compile
- Null-check type errors in `test` conditions (e.g. checking a `String` for empty when
  it may instead be null, or the reverse)

Do not report in the following cases:
- The parameter is declared non-null/required at the mapper interface method signature
- An enclosing `<if>`/`<choose>` already rules out the null case for this branch

#### Thread Safety
- Rarely applicable: mapper XML defines per-call SQL templates with no shared mutable
  state across invocations

Do not report in the following cases:
- Ordinary per-request mapper execution with no shared mutable state in the mapper
- A statically cached `SqlSession`/mapper instance used only per its documented contract

#### SQL Injection
- `${}` string substitution used to concatenate untrusted input directly into a SQL
  statement, instead of `#{}` parameter binding
- LIKE conditions or ORDER BY clauses built by direct string concatenation of user
  input instead of safe parameter binding or an allow-listed column list

Do not report in the following cases:
- The value is bound via `#{}`, which MyBatis parameterizes and escapes automatically
- The `${}` value is a fixed, application-controlled constant, never user input

#### Unbounded Resource Consumption
- A query with no WHERE condition or with a condition that will not meaningfully
  restrict result size, executed against a table expected to grow without bound
- A query capable of returning a large dataset with no `LIMIT`/pagination parameter

Do not report in the following cases:
- The query already includes a `LIMIT`/pagination clause or `RowBounds` parameter
- The table is bounded in size by design (a fixed lookup/config table)

#### Swallowed Errors
- Result-mapping logic that catches a mapping/conversion exception and silently
  substitutes a default row instead of surfacing the failure
- A `<selectKey>`/generated-key failure path with no propagation to the caller

Do not report in the following cases:
- The failure is logged and rethrown or surfaced as an explicit application error
- The masked failure is a documented, unreachable internal invariant
