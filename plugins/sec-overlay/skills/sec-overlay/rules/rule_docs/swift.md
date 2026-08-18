> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear — a false
> alarm costs more reviewer trust than a missed minor issue.

#### Force Unwrap and Implicitly Unwrapped Optionals
- Force unwrap (`!`) on an `Optional`, `try!`, or `as!` where the value can genuinely be
  `nil` or the wrong type at runtime, not already ruled out by an earlier guard
- An implicitly unwrapped optional (`var x: T!`) read before the initialization point
  that sets it guarantees a value (a lifecycle callback that can run out of order)
- `Array`/`Dictionary` subscript access assumed to succeed when the index/key can be
  out of range or absent

Do not report in the following cases:
- The `nil` case is already ruled out by an earlier `guard let`/`if let`/`??` in the
  same function, or by a type contract the caller has already validated
- The implicitly unwrapped optional is a required dependency-injection point set
  before every use by a documented initializer or lifecycle contract (`viewDidLoad`
  after `init`)

#### Thread Safety and Actor Isolation
Only flag thread safety issues when the diff or surrounding file shows evidence of
concurrent or actor-based execution:
- Mutable shared state accessed from multiple `DispatchQueue`s, threads, or Tasks
  without a lock, a serial queue, or actor isolation protecting it
- `@unchecked Sendable` applied to a type whose internal state is not actually
  synchronized, or a non-`Sendable` value captured across an isolation boundary
- A `Task.detached` or an escaping closure capturing `self`/mutable state without
  confining access to the owning actor or main-actor context it depends on

Do not report in the following cases:
- Local variables within a function (each task/thread has its own copy)
- Single-threaded, non-concurrent context with no evidence of shared mutation
- The code already uses correct actor isolation, a serial queue, or a lock, and no
  boundary crossing bypasses it

#### Injection (SQL and XSS)
- SQL built by string concatenation or interpolation instead of a parameterized query
  (SQLite's bound parameters, Core Data predicates, or an ORM's query builder)
- Untrusted request data written into an HTML/`WKWebView` response without escaping,
  enabling stored or reflected XSS
- Untrusted data interpolated into a shell command or `Process` argument list without
  validation

Do not report in the following cases:
- The value is a literal constant, or is validated/escaped immediately before use by a
  function whose body is visible in the diff or surrounding file
- The rendering layer's autoescaping is active and the output is not explicitly marked
  safe/raw

#### Resource Leaks
- A file handle, `URLSession` task, or Core Data context not closed/invalidated on
  every reachable path, including an error path
- A retain cycle between a closure and `self` missing `[weak self]`/`[unowned self]`
  where the closure outlives the expected scope (a stored completion handler, a
  notification observer)
- A registered `NotificationCenter` observer or KVO observation never removed on
  deinitialization

Do not report in the following cases:
- The type already uses `[weak self]`/`[unowned self]` correctly, or ARC already
  reclaims the object with no cycle present
- The resource is owned by a framework-managed lifecycle (a view controller's own
  `URLSession`, a `@FetchRequest`) visible in context

#### Swallowed Errors
- An empty `catch` block, or a `catch` that logs nothing and substitutes a misleading
  default, discarding a failure the caller needs to know about
- `try?` used to convert a meaningful error into `nil` on a path where the caller
  cannot distinguish "absent" from "failed"
- The original error's underlying cause lost by wrapping it in a new error type with
  no reference to the original

Do not report in the following cases:
- The `catch` block re-throws, logs at an appropriate level, or returns an explicit
  error result the caller checks
- The `try?` is a documented best-effort probe where `nil` and failure are equivalent
  for the caller's purpose
