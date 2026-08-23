> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Nil Dereference and Lifetime Safety
- References, pointers, or `openArray` views that outlive the storage they refer to,
  especially addresses derived from stack locals or temporary sequences
- `cast`, `addr`, `unsafeAddr`, or manual allocation used without a locally established
  type, bounds, ownership, and lifetime invariant

Do not report in the following cases:
- An earlier check in the same scope already establishes the reference is non-nil/live
- Ordinary managed references or value copies with no evidence of a lifetime defect

#### Concurrency and Async
- Shared mutable state accessed by threads without a lock, channel, atomic operation,
  or established single-owner design
- Locks held across blocking operations, callbacks, or `await`, creating deadlock or
  starvation risk

Do not report in the following cases:
- The shared state is already protected by a lock/channel visible in context
- Thread-local state with no cross-thread access

#### Injection
- Untrusted text incorporated into `execShellCmd`, a shell invocation, SQL
  construction, or generated Nim/compiler invocations without strict validation
- User-controlled data passed to path access or deserialization without validation or
  parameterization

Do not report in the following cases:
- The value is a literal constant or validated/escaped immediately before use
- The call uses a parameterized API rather than raw string concatenation

#### Resource Cleanup
- Resources acquired without `defer`, `try/finally`, or an ownership abstraction when
  an exception or early return can leak them
- Mismatched allocation/deallocation APIs, double destruction, or missing cleanup for
  manually managed resources

Do not report in the following cases:
- The resource is already released by an enclosing `defer`/`try-finally` in context
- Managed-memory (ARC/ORC) values with no manual allocation involved

#### Swallowed Errors
- `except:` or overly broad exception handling that swallows defects or actionable
  context and returns a plausible default result
- Error-code or `Option`/`Result` values ignored at a boundary where failure changes
  correctness or leaves partial state behind

Do not report in the following cases:
- The handler re-raises, logs at an appropriate level, or checks the `Result` explicitly
- The masked failure is a documented, unreachable internal invariant
