> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear — a false
> alarm costs more reviewer trust than a missed minor issue.

#### Null and Undefined Dereference
- Optional chaining (`?.`) omitted on a property access, array index, or method call
  where the value can legitimately be `null`/`undefined` (an API response, a `Map.get`,
  a `find()` result, a React ref before mount)
- A non-null assertion (`!`) or `as` cast used to silence the type checker on a value
  the runtime can still produce as `null`/`undefined`
- Destructuring a possibly-`undefined` object or array element without a default

Do not report in the following cases:
- The `null`/`undefined` case is already ruled out by an earlier guard, a type narrowing
  `if`, or a required (non-optional) prop/parameter type
- The value comes from a constant literal or a schema-validated payload already
  checked in the same function

#### Concurrency and Unhandled Promise Rejection
- A `Promise` or `async` call whose rejection is never caught (`.catch`, `try`/`await`,
  or a global `unhandledrejection` handler) on a path where failure is expected
- `async` work started in `useEffect`/a component lifecycle without a cleanup guard,
  letting a resolved promise update state after unmount
- Concurrent writes to shared module-level or global state from parallel async
  operations (`Promise.all`) with no ordering guarantee, where order matters

Do not report in the following cases:
- The promise chain already ends in `.catch`, or the caller awaits it inside a
  `try`/`catch` visible in the diff or surrounding file
- The async call has no side effect that outlives its own scope (a pure computation)

#### Injection (SQL, XSS, and Unsafe `dangerouslySetInnerHTML`)
- SQL or NoSQL query strings built by concatenation or template literals instead of a
  parameterized query or query-builder API
- `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, or `document.write` set from
  untrusted data without sanitization (DOMPurify or equivalent)
- `eval`, `new Function(...)`, or a dynamic `require`/`import` reached by untrusted
  input

Do not report in the following cases:
- The value is a literal constant, or is sanitized/escaped immediately before use by a
  function whose body is visible in the diff or surrounding file
- The framework's default JSX text interpolation is used (React/Vue auto-escape text
  content; only the "dangerous" APIs above need review)

#### Resource Leaks
- An event listener, `setInterval`/`setTimeout`, `WebSocket`, or subscription created
  in a component or module without a matching removal/cleanup on teardown
  (`useEffect` cleanup, `componentWillUnmount`, `unsubscribe()`)
- A file handle, database connection, or stream (Node.js) not closed on every path,
  including an error path
- An `AbortController` never wired to a `fetch`/long-running request that should be
  cancelled when the caller navigates away or unmounts

Do not report in the following cases:
- The listener/timer/subscription is intentionally process-lifetime (a singleton
  service, a top-level script) with no teardown expected
- The resource is already released by an enclosing framework lifecycle or a
  library-managed cleanup visible in context

#### Swallowed Errors
- An empty `catch` block, or a `catch` that logs nothing and returns a misleading
  default, discarding a failure the caller needs to know about
- A rejected promise silently ignored (a `.then()` with no `.catch`, a fire-and-forget
  async call with no error path)
- An error re-thrown as a generic `Error` that drops the original error/stack, losing
  the ability to distinguish failure causes upstream

Do not report in the following cases:
- The `catch` block re-throws, logs at an appropriate level, or returns an explicit
  error result the caller checks
- The ignored rejection is a documented best-effort side effect (analytics, telemetry)
  with no correctness impact
