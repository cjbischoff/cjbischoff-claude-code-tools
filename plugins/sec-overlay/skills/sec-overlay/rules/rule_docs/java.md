> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear — a false
> alarm costs more reviewer trust than a missed minor issue.

#### Null Dereference and Optional Misuse
- A field, method return, or map lookup reaching code that assumes a value, when an
  upstream call, `Map.get(...)`, or a default parameter can legitimately return `null`
- `Optional.get()` called without `isPresent()`/`ifPresent`/`orElseThrow` guarding it
- Chained method calls (`a.getB().getC()`) where any link in the chain can return `null`
- Autoboxing a nullable `Integer`/`Long`/`Boolean` wrapper into a primitive, throwing an
  unboxing NPE on a reachable `null`

Do not report in the following cases:
- The `null` case is already ruled out by an earlier `if`/`Objects.requireNonNull` in
  the same method, or by a type contract the caller has already validated
- The value is a `final` field pointing to an immutable object, or a required
  constructor parameter with no default

#### Thread Safety and Non-Thread-Safe Collections
Only flag thread safety issues when the diff or surrounding file shows evidence of
multi-threaded invocation:
- A check-then-act race on shared state without `synchronized`, a `Lock`, or an atomic
  class covering both steps
- Concurrent writes to a non-thread-safe collection (`ArrayList`, `HashMap`,
  `HashSet`) shared across threads instead of a concurrent or synchronized equivalent
- Unsafe lazy initialization or double-checked locking in a singleton or cache without
  a `volatile` field or a correct holder-class idiom

Do not report in the following cases:
- Local variables within a method (each thread has its own copy)
- Single-threaded context with no evidence of concurrent invocation
- Read-only access to shared, immutable data, or a reference to a `final` field
  pointing at an immutable object
- The code already uses `synchronized`, `Lock`, `java.util.concurrent` atomics, or a
  concurrent collection correctly
- A builder's in-progress build phase or a temporary data-transfer object, neither
  designed for concurrent use

#### Injection (SQL and XSS)
- SQL built by string concatenation instead of a `PreparedStatement` parameter or the
  ORM's query builder
- Untrusted request data (parameters, headers, form fields) written into an HTML
  response without escaping, enabling stored or reflected XSS
- Untrusted data interpolated into a `ProcessBuilder`/`Runtime.exec` command string
- Reflection or a scripting engine (`ScriptEngine`, JEXL) evaluating untrusted input

Do not report in the following cases:
- The value is a literal constant, or is validated/escaped immediately before use by a
  function whose body is visible in the diff or surrounding file
- The templating engine's autoescaping is active and the output is not explicitly
  marked safe/unescaped

#### Resource Leaks
- Files, sockets, streams, or database connections/statements opened without
  try-with-resources, risking a leak on an early return or an exception
- A resource acquired in a `try` whose `finally` cleanup is missing or incomplete on
  the error path
- An `AutoCloseable` resource bypassed in favor of manual `open()`/`close()` pairs

Do not report in the following cases:
- A short-lived CLI tool where process exit reclaims the resource
- The resource is already managed by an enclosing try-with-resources block or a
  framework-managed lifecycle (a connection pool, a DI container) visible in context

#### Swallowed Errors
- An empty `catch` block, or a `catch (Exception e)` that logs nothing and re-throws
  nothing, discarding the failure
- The original exception's cause lost by throwing a new exception without
  `initCause`/the chaining constructor
- A broad `try` block wrapping far more code than the line that can actually throw,
  hiding where the error originates

Do not report in the following cases:
- The `catch` block re-throws, logs at an appropriate level, or returns an explicit
  error result the caller checks
- The exception is an unchecked internal invariant assertion, not external-input
  validation
