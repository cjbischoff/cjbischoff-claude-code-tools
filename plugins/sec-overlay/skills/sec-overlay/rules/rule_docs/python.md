> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear — a false
> alarm costs more reviewer trust than a missed minor issue.

#### Null and None Dereference
- `None` reaching code that assumes a value, when an upstream call, default parameter, or
  `dict.get(...)` can legitimately return `None`
- Attribute or item access on the result of a function documented or observed to return
  `Optional[...]` without a guard
- Dictionary access by key without handling the missing-key case (`d[k]` vs `d.get(k)`)
- Chained attribute access (`a.b.c`) where any link in the chain can be `None`

Do not report in the following cases:
- The `None` case is already ruled out by an earlier `if`/`assert`/`raise` in the same
  function, or by a type contract the caller has already validated
- The value is a required, non-Optional constructor or function parameter with no default

#### Thread Safety
Only flag thread safety issues when the diff or surrounding file shows evidence of
multi-threaded, multi-process, or async invocation:
- Check-then-act races on shared state without a `Lock`, or non-atomic compound updates
  assumed to be atomic
- Module-level or class-level mutable state (lists, dicts, caches) mutated across
  requests or threads without synchronization
- Blocking calls (synchronous I/O, `time.sleep`, CPU-heavy work) inside `async def`,
  stalling the event loop

Do not report in the following cases:
- Local variables within a function (each thread has its own copy)
- Single-threaded context with no evidence of concurrent invocation
- Read-only access to shared, immutable data
- The code already uses a `Lock`, `asyncio.Lock`, atomic primitive, or other correct
  synchronization mechanism

#### Injection (SQL and XSS)
- SQL built by string concatenation or an f-string instead of a parameterized query or
  the ORM's query builder
- Untrusted request data (query params, form fields, headers, cookies) written into an
  HTML response without escaping, enabling stored or reflected XSS
- Untrusted data passed to `subprocess` with `shell=True`, or interpolated into a shell
  command string
- `eval`, `exec`, or `compile` applied to untrusted input

Do not report in the following cases:
- The value is a literal constant, or is validated/escaped immediately before use by a
  function whose body is visible in the diff or surrounding file
- The templating engine's autoescaping is active and the output is not explicitly
  marked safe/unescaped

#### Resource Leaks
- Files, sockets, locks, or database connections opened without a `with` statement,
  risking a leak on an early return or an exception
- A resource acquired in a `try` whose `finally` cleanup is missing or incomplete on the
  error path
- A context manager available on the type but bypassed in favor of manual
  `open()`/`close()` pairs

Do not report in the following cases:
- A short-lived script where the process exit reclaims the resource
- The resource is already managed by an enclosing `with` block or a framework-managed
  lifecycle visible in the surrounding file

#### Swallowed Errors
- A bare `except:` or a broad `except Exception:` that logs nothing and re-raises
  nothing, discarding the failure
- The original traceback lost by raising a new exception without `raise ... from err`
- A broad `try` block wrapping far more code than the line that can actually fail,
  hiding where the error originates

Do not report in the following cases:
- The `except` block re-raises, logs at an appropriate level, or returns an explicit
  error result the caller checks
- `assert` is used for an internal invariant, not for validating external input
