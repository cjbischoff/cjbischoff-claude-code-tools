> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear — a false
> alarm costs more reviewer trust than a missed minor issue. This is the fallback doc
> for any file whose extension does not match a language-specific rule doc.

#### Null and Absent-Value Dereference
- A value from a call, lookup, or external input reaching code that assumes a usable
  result, when the language's own null/absent/`Optional`/`Result` convention shows the
  operation can legitimately fail or return nothing
- A chained access where any link in the chain can be null/absent, with no guard
  between the fallible call and the dereference

Do not report in the following cases:
- The null/absent case is already ruled out by an earlier check in the same function
- The value is a required parameter, a constant, or a type the language guarantees is
  always present

#### Thread Safety
Only flag thread safety issues when the diff or surrounding file shows evidence of
concurrent or parallel execution:
- Shared mutable state read and written from more than one thread, process, or async
  task without a lock, atomic primitive, or equivalent synchronization
- A check-then-act sequence on shared state that can interleave with another
  thread/task between the check and the act

Do not report in the following cases:
- Local variables within a function, never shared across threads/tasks
- Single-threaded or single-task context with no evidence of concurrent invocation
- The code already uses correct synchronization for the shared state

#### Injection (SQL and XSS)
- A query string assembled by concatenating untrusted input instead of using
  parameter binding or a query-builder API
- Untrusted data written into an HTML, template, or shell context without
  escaping/sanitization appropriate to that context

Do not report in the following cases:
- The value is a literal constant, or is validated/escaped immediately before use by a
  function whose body is visible in the diff or surrounding file
- The templating layer's autoescaping is active and the output is not explicitly
  marked safe/raw

#### Resource Leaks
- A file, socket, lock, or connection acquired without a guarantee of release on every
  reachable path, including an error or early-return path
- A resource whose owning scope ends without releasing it, when the language provides
  a scoped-release idiom (context manager, `try`-with-resources, RAII, `defer`) that
  the surrounding code does not use

Do not report in the following cases:
- The resource is already released by an enclosing scoped-release construct or a
  framework-managed lifecycle visible in context
- A short-lived script or process where exit reclaims the resource

#### Swallowed Errors
- An empty error-handling block, or one that discards a failure and substitutes a
  misleading default, hiding a failed operation from the caller
- An error's original cause lost when it is converted, wrapped, or re-raised without
  preserving the source of the failure

Do not report in the following cases:
- The error-handling block re-raises, logs at an appropriate level, or returns an
  explicit error result the caller checks
- The error is a documented, unreachable internal invariant, not external-input
  validation
