> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear. Adapted from open-code-review (Apache-2.0). Review only what is observable in the schema (SDL) or
> operation text under review; do not infer resolver behavior that lives outside it.

#### Nullability and Optional-Field Misuse
- A field that can never legitimately be null typed as nullable, or a genuinely
  optional field typed non-null, hiding required-vs-optional intent from clients
- Making a previously nullable input field or argument non-null, or adding a new
  required (non-null, no-default) argument to an existing field — a breaking change
  for existing clients

Do not report in the following cases:
- The change is a purely additive new optional (nullable or defaulted) argument
- Nullability already matches the field's documented semantics

#### Resolver Concurrency and Non-Deterministic Default Resolution
Schemas have no threads, but default-value resolution across resolver versions has
an analogous ordering hazard:
- A newly added field default or enum default that depends on server-side resolver
  state which can differ between requests in the same rollout window, when the diff
  shows no version gate
- Do not report in the following cases:
  - The default is a static schema-declared value with no resolver-side variability
  - No evidence in the diff of a multi-version rollout

#### Injection and Introspection Exposure
- A field carrying clearly sensitive data (token, secret, password, or PII by name or
  description) exposed without an accompanying auth-related directive or comment
- An explicit directive, configuration, or comment in the diff that enables
  introspection on a surface documented or implied to be untrusted/public
- An argument accepting a raw string later used as a query/command fragment, per the
  field's own description, with no validation guidance at the boundary

Do not report in the following cases:
- The field is already gated by an auth directive (`@auth`, `@requiresRole`, etc.)
- Validation is enforced in resolver code and clearly documented outside the schema

#### Unbounded Queries and Resource Exhaustion
- A list field returning a collection without a pagination or limit argument
  (`first`/`last`/`limit`/`after`), allowing an unbounded result set
- Deeply nested or recursive selections/types with no documented depth or complexity
  limit, a query-depth denial-of-service surface

Do not report in the following cases:
- A depth/complexity limit is enforced outside the schema and clearly documented
- The list is bounded by a fixed, non-recursive relationship (e.g. always ≤ a few items)

#### Swallowed Errors in Deprecated-Field Usage
- An operation or fragment selecting a `@deprecated` field with no `reason` given for
  the deprecation, masking why the field is unsafe to rely on going forward
- A schema change that silently drops a field's error/partial-result signal (e.g.
  replacing a typed error union with a bare nullable field) without discussion in the
  diff

Do not report in the following cases:
- The deprecation already carries a clear `reason` and a migration path
- The nullable field was already the documented mechanism for representing failure
