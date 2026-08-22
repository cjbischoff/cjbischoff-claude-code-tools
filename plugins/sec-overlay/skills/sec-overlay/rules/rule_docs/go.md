> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear — a false
> alarm costs more reviewer trust than a missed minor issue.

#### Nil Dereference, Nil Maps, and Unchecked Type Assertions
- A typed nil pointer, map, slice, function, channel, or error stored in a non-nil
  interface and later treated as absent, without checking the concrete assignment first
- A nil map written to (`m[k] = v` on a `var m map[K]V`), or a nil pointer dereferenced
  on a path a constructor or upstream call can actually produce
- A two-value type assertion (`v, ok := x.(T)`) written as the single-value form
  (`v := x.(T)`), panicking when the assertion fails on reachable input
- Ignoring the returned `error` from a call and continuing as if the operation succeeded

Do not report in the following cases:
- The nil case is already ruled out by an earlier `if`/type check in the same function
- The value is a required, always-initialized struct field or constructor parameter

#### Thread Safety and Goroutine Capture
Only flag thread safety issues when the diff or surrounding file shows evidence of
concurrent invocation across goroutines:
- Unsynchronized concurrent reads/writes of maps, slices, pointers, counters, or
  compound state; check-then-act sequences that can interleave
- Copying a value after first use when it contains `sync.Mutex`, `sync.RWMutex`,
  `sync.Once`, or other non-copyable synchronization primitives
- Loop-variable or mutable outer-variable capture in a goroutine or callback where a
  closure can observe a later value, in a module whose `go` directive predates 1.22
- Holding a mutex across blocking I/O, channel operations, or long CPU work when
  another goroutine needs the lock to progress

Do not report in the following cases:
- Local variables within a function (each goroutine has its own copy)
- Single-goroutine context with no evidence of concurrent invocation
- The code already uses a `Mutex`, `RWMutex`, atomic primitive, or channel-based
  synchronization correctly
- A module's `go` directive is 1.22+, where each loop iteration gets its own variable

#### Injection (SQL and XSS)
- SQL built by string concatenation or `fmt.Sprintf` instead of a parameterized query
  (`database/sql`'s `?`/`$1` placeholders) or the ORM's query builder
- Untrusted request data written into an HTML response through `text/template` instead
  of `html/template`, or a trusted-template type constructed from untrusted content
- Untrusted data interpolated into a shell command string, or passed to `os/exec` in a
  way that still requires validation despite the argument-array form being safer than a
  shell

Do not report in the following cases:
- The value is a literal constant, or is validated/escaped immediately before use by a
  function whose body is visible in the diff or surrounding file
- `html/template`'s autoescaping is active and the output is not explicitly marked safe

#### Resource Leaks
- `http.Response.Body`, `sql.Rows`, files, sockets, or other closable resources not
  closed on all reachable paths after acquisition, including an early-return path
- `defer` inside a loop that can run many iterations, delaying resource release until
  function return instead of each iteration's end
- A timer or ticker retained by its owner and left running after work ends on a
  pre-1.23 Go version, where it can fire and retain reachable state

Do not report in the following cases:
- The resource is handed to a caller or framework that owns its closure
- A short-lived script or CLI command where process exit reclaims the resource
- The module targets Go 1.23+ and the only concern is an unstopped timer/ticker being
  collected by the runtime rather than leaking a held resource

#### Swallowed Errors
- An error returned from a call that is ignored, overwritten, or converted into a
  success/default value that hides a failed operation
- Error wrapping that loses the original cause (`fmt.Errorf("...: %v", err)` when a
  caller needs `errors.Is`/`errors.As`) instead of using `%w`
- Deferred cleanup that overwrites a primary error, or drops a meaningful
  `Close`/`Commit`/`Rollback` error without logging or returning it

Do not report in the following cases:
- A deliberately best-effort operation whose ignored failure is safe and documented
- The error is a documented, unreachable internal invariant, not an external contract
