> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Partial Functions and Optional Values
- `head`, `tail`, `fromJust`, `fromRight`, `!!`, `foldl1`, `read`, `error`, or
  `undefined` applied to input with no locally proven non-empty/valid invariant
- Non-exhaustive pattern matches in function equations, `case`, or `do` bindings when a
  reachable constructor would fail at runtime

Do not report in the following cases:
- The same function already validated the invariant earlier, or the type encodes it
- The partial call marks a deliberately unreachable internal-invariant branch

#### MVar, STM, and Thread Safety
- Shared mutable state updated from multiple threads without an `MVar`, `TVar`, or
  atomic primitive establishing single ownership
- A `takeMVar`/work/`putMVar` sequence that can be interrupted by an async exception,
  leaving the `MVar` empty; or blocking/unbounded work performed inside `atomically`

Do not report in the following cases:
- The state is thread-local or owned by a single `forkIO`/`async` task
- The code already uses `modifyMVar` or an equivalent exception-safe combinator

#### Injection
- External input passed to `System.Process.shell`, a raw shell command, or SQL/query
  construction without strict validation or parameterization
- Template Haskell or quasiquotation that incorporates untrusted data into generated,
  executable code

Do not report in the following cases:
- The call uses `proc` with an explicit argument list, not a shell string
- The value is a literal constant or validated immediately before use

#### Resource Leaks
- `IO` resources (`Handle`, socket, connection) opened without `bracket`, `withFile`,
  or `finally`, leaking on an exception or early-return path
- Cleanup implemented as a plain sequential action after the main operation instead of
  an exception-safe combinator

Do not report in the following cases:
- The resource is already released by an enclosing `bracket`/`withFile` in context
- A short-lived script where process exit reclaims the resource

#### Swallowed Errors
- `catch`/`try` at `SomeException` that unintentionally swallows async exceptions
  (cancellation) instead of catching the expected exception type
- An exception handler that discards the original cause or substitutes a plausible
  default, hiding a failed operation from the caller

Do not report in the following cases:
- The handler rethrows, logs at an appropriate level, or returns an explicit `Either`
- The error path is a documented, unreachable internal invariant
