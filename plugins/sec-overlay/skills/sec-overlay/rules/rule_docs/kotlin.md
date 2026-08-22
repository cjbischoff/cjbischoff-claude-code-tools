> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear — a false
> alarm costs more reviewer trust than a missed minor issue.

#### Null Safety and Platform-Type Nullability
- The not-null assertion operator (`!!`) used on a value that can genuinely be `null`
  at runtime, especially a platform type crossing the Java interop boundary with no
  Kotlin-visible nullability annotation
- A Java method call returning a platform type (`String!`) treated as non-null without
  a `?.`/`?:`/explicit check, when the Java source or annotation does not guarantee it
- `lateinit var` accessed before initialization on a reachable path (a field read
  before the lifecycle method that sets it has run)

Do not report in the following cases:
- The `null` case is already ruled out by an earlier `?.`/`?:`/smart-cast check in the
  same function
- The platform type is documented `@NonNull`/`@NotNull` at the Java declaration, or the
  value is a required constructor parameter

#### Thread Safety and Coroutine Scope Leaks
Only flag thread safety issues when the diff or surrounding file shows evidence of
concurrent or coroutine-based execution:
- `GlobalScope.launch`/`async` used for work tied to a component's lifecycle, leaking
  the coroutine past the component's destruction instead of a structured scope
  (`viewModelScope`, `lifecycleScope`, a scope tied to a parent job)
- Shared mutable state (a `var`, a mutable collection) written from multiple
  coroutines/threads without a `Mutex`, an atomic type, or confinement to a single
  dispatcher
- A `suspend` function performing blocking I/O on `Dispatchers.Main` instead of
  `Dispatchers.IO`, or missing `withContext` around a blocking call

Do not report in the following cases:
- Local variables within a function (each coroutine has its own copy)
- Single-coroutine, non-concurrent context with no evidence of shared mutation
- The code already uses a `Mutex`, an atomic type, or single-dispatcher confinement
  correctly, or the scope is already structured and cancelled with its owner

#### Injection (SQL and XSS)
- SQL built by string concatenation or template interpolation instead of a
  parameterized query (Room's `@Query` with bound args, JDBC `PreparedStatement`, or
  Exposed's query builder)
- Untrusted request data written into an HTML/WebView response without escaping,
  enabling stored or reflected XSS
- Untrusted data interpolated into a shell command or `ProcessBuilder` invocation

Do not report in the following cases:
- The value is a literal constant, or is validated/escaped immediately before use by a
  function whose body is visible in the diff or surrounding file
- The templating or WebView layer's autoescaping is active and the output is not
  explicitly marked safe

#### Resource Leaks
- A file, socket, cursor, or database connection opened without `use { }` or an
  equivalent try-finally, risking a leak on an early return or an exception
- A coroutine-scoped resource acquired without tying its release to the scope's
  cancellation (no `use`, no `invokeOnCompletion`, no `finally`)
- A registered `Closeable`, listener, or observer never unregistered on component
  teardown

Do not report in the following cases:
- The resource is already wrapped in `use { }`, try-with-resources, or a
  framework-managed lifecycle (Room, Retrofit, DI-scoped) visible in context
- A short-lived CLI/script where process exit reclaims the resource

#### Swallowed Errors
- An empty `catch` block, or a `catch (e: Exception)` that logs nothing and returns a
  misleading default, discarding a failure the caller needs to know about
- A `Result.failure`/`runCatching` result whose failure branch is never inspected
  (`.getOrNull()` used without checking why it was null)
- The original exception's cause lost by throwing a new exception without passing
  `cause = e`

Do not report in the following cases:
- The `catch` block re-throws, logs at an appropriate level, or returns an explicit
  error result the caller checks
- The exception is an unchecked internal invariant assertion, not external-input
  validation
