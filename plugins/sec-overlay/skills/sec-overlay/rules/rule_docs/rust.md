> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear — a false
> alarm costs more reviewer trust than a missed minor issue.

#### Panics on Fallible Values (`unwrap`/`expect`)
- `unwrap()`, `expect()`, or `panic!` on a `Result`/`Option` in a production or library
  path where the failure is recoverable and can be propagated with `?` or a typed error
- `todo!()` or `unimplemented!()` left on a path reachable by ordinary input, not a
  documented programmer contract
- A public API that panics on ordinary invalid input instead of returning a typed
  error, unless the panic documents a clear internal invariant

Do not report in the following cases:
- The panic is already ruled out by an earlier check in the same function, or the
  value is a compile-time-known constant that cannot be `None`/`Err`
- The `unwrap`/`expect` is in test code (`#[test]`, `#[cfg(test)]`) or a documented,
  unreachable internal invariant

#### Thread Safety and Lock-Order Inversion
Only flag thread safety issues when the diff or surrounding file shows evidence of
multi-threaded or async invocation:
- Holding a `Mutex`/`RwLock` guard across blocking I/O, a `.await` point, or a call
  into user code when another thread/task needs the lock to progress
- Two or more locks acquired in inconsistent order across call sites, risking deadlock
- Check-then-act races around shared state, cache initialization, or atomics without a
  compound synchronization primitive covering both steps
- An unsafe `Send`/`Sync` implementation that does not prove all contained state is
  thread-safe under the documented invariants

Do not report in the following cases:
- Local variables within a function (each thread/task owns its stack)
- Single-threaded context with no evidence of concurrent invocation
- The lock is already released (via scope or an explicit `drop`) before the blocking
  call or `.await` point
- The code already uses a correctly-ordered lock hierarchy or a lock-free primitive

#### Injection (SQL and XSS)
- SQL built by string concatenation or `format!` instead of a parameterized query
  (sqlx's `query!`, Diesel's query builder) with bound parameters
- Untrusted request data written into an HTML response without escaping (askama,
  tera) enabling stored or reflected XSS
- Untrusted data interpolated into a shell command string, or passed to
  `std::process::Command` in a way that still requires validation of option-like values

Do not report in the following cases:
- The value is a literal constant, or is validated/escaped immediately before use by a
  function whose body is visible in the diff or surrounding file
- The templating engine's autoescaping is active and the output is not explicitly
  marked safe

#### Resource Leaks
- A file, socket, or lock guard held longer than the surrounding block requires, or
  never explicitly released on an early-return path in a function with manual cleanup
- A spawned task's `JoinHandle` dropped when a failure, cancellation, or shutdown
  signal still needs to be observed
- A `Drop` implementation that can panic, or that skips cleanup on a path an earlier
  `return`/`?` bypasses

Do not report in the following cases:
- The type's `Drop` implementation already guarantees release; RAII covers the
  ordinary case with no early-return bypass
- A short-lived binary where process exit reclaims the resource

#### Swallowed Errors
- A `Result`/`Option` value ignored (no `?`, no `match`, no `.expect` with a clear
  message) or mapped to a misleading default that hides a failed operation
- An error converted to a string too early, or discarded, instead of preserving the
  original error and adding context at a boundary (`.context(...)`, `#[source]`)
- A broad `match`/`if let` arm swallowing every error variant identically, hiding
  which failure actually occurred

Do not report in the following cases:
- The error is explicitly logged and the function's documented contract is
  best-effort, evident from the surrounding code
- The ignored `Result` is `()`-typed and documented as infallible in practice (for
  example, writing to an in-memory buffer)
