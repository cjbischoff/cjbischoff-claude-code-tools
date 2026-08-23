> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Nothing, Missing, and Optional Handling
- Conflating `nothing` (absence) and `missing` (unknown), e.g. `x == nothing` instead
  of `isnothing(x)` / `x === nothing`
- Functions that sometimes `throw` and sometimes `return nothing` for the same failure
  mode, forcing callers to handle both inconsistently

Do not report in the following cases:
- An earlier `isnothing`/`ismissing` check in the same function already guards the value
- The value is a required, always-populated struct field or constant

#### Concurrency and Shared State
- Data races on shared mutable state updated from `Threads.@threads`,
  `Threads.@spawn`, or `@async` tasks without a lock, atomic, or per-task accumulation
- Tasks spawned in a loop that capture and mutate a variable declared outside the loop,
  so every task shares one binding

Do not report in the following cases:
- `@async` used only for cooperative I/O scheduling with no shared mutable state
- The shared state is already protected by a lock/atomic visible in context

#### Injection
- `eval`, `Meta.parse`, `include_string`, or `@eval` applied to untrusted or externally
  derived input
- Untrusted input interpolated into an explicit shell invocation (`sh -c`, `bash -c`),
  or SQL/file paths built through unchecked string concatenation of external input

Do not report in the following cases:
- The value is a literal constant or validated/escaped immediately before use
- A plain backtick command interpolates arguments without invoking a shell

#### Resource Management
- Files, streams, or connections opened without `close`/`do`-block cleanup, leaking on
  an early return or exception path
- `ccall`/`unsafe_load`/`unsafe_wrap`/`pointer` used without validating length,
  alignment, lifetime, or null-ness of the underlying memory

Do not report in the following cases:
- The resource is opened via a `do`-block that guarantees `close` on exit
- A short-lived script where process exit reclaims the resource

#### Swallowed Errors
- Swallowing exceptions with an empty `catch` block or rethrowing without preserving
  context, hiding real errors
- Relying on `@assert` for input validation or security checks when assertions can be
  disabled, instead of an explicit `throw`

Do not report in the following cases:
- The catch block logs at an appropriate level or rethrows a wrapped error
- The masked failure is a documented, unreachable internal invariant
