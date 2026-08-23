> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear. Adapted from open-code-review (Apache-2.0).

#### Optional Fields and Presence Semantics
- Missing `optional` (proto3) where absence must be distinguishable from the field's
  zero value, causing a consumer to treat "not set" as "explicitly zero"
- A `oneof` whose zero-state leaves an ambiguous or invalid representation when an
  explicit sentinel was clearly intended by the surrounding fields

Do not report in the following cases:
- The field's zero value is never semantically distinct from "unset" for the domain
  it models
- The message already models presence correctly via `oneof` or `optional`

#### Concurrency: Migration Ordering (Wire and Registry Consistency)
Proto files have no runtime threads to race, but schema rollout has an ordering
hazard worth the same caution:
- A field renumbered or a `oneof` restructured in the same change that also updates
  server and client stubs, without a documented rollout order, risking clients on
  the old schema misreading the new wire format during deploy
- Do not report in the following cases:
  - The change is purely additive (new field, new number) with no reuse of an
    existing tag
  - No evidence in the diff of a coordinated multi-service rollout

#### Injection and Untrusted Payload Handling
- `google.protobuf.Any` accepted from untrusted input without type allowlisting
  before unpacking
- A string field carrying a file path, URL, or SQL fragment used downstream without
  documented validation, when the field's name/comment indicates untrusted origin
- Secrets, tokens, or credentials embedded in field defaults, examples, or comments

Do not report in the following cases:
- The `Any` type is unpacked only after checking `type_url` against a fixed allowlist
- Validation is enforced at the service boundary and clearly documented outside the
  schema

#### Resource Limits (Unbounded Fields and Recursion)
- Unbounded `repeated`/`map` fields on a message accepted from untrusted input with
  no documented application-level size limit
- Recursive message definitions reachable from an untrusted RPC input with no
  documented depth limit, enabling a stack-exhaustion payload
- Unbounded client/server streaming RPCs with no documented flow control or deadline

Do not report in the following cases:
- The limit is enforced outside the schema (gateway, interceptor) and that boundary
  is clearly documented
- The message is only ever produced internally, never accepted from an external caller

#### Breaking Changes as Silent Error Sources
- Reusing or renumbering a field tag, or deleting a field without adding its number
  and name to `reserved`, which makes old and new binaries silently misinterpret each
  other's data instead of raising a decode error
- Changing a field's type or label in a way that breaks wire compatibility, causing a
  decode to silently produce wrong values rather than fail

Do not report in the following cases:
- The field being removed/renumbered was never released to an external consumer
- The change is a purely additive new field or enum value with a fresh number
