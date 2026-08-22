> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear — a false
> alarm costs more reviewer trust than a missed minor issue.

#### Null, Loose-Comparison, and Type-Juggling Errors
- Loose comparison (`==`/`!=`) whose coercion can make distinct security- or
  domain-sensitive values compare equal (`"0" == false`, `"abc" == 0` pre-PHP 8)
- `empty()` or truthiness checks that treat `0`, `"0"`, `false`, `null`, and an empty
  string as equivalent when those states carry different meaning
- `isset()` used when a present key holding `null` must be distinguished from a
  missing key; `array_key_exists()` is required when presence, not non-nullness, is
  the contract
- A nullable or `false`-returning function's failure value reaching code that assumes
  a usable object, scalar, or resource, without a guard

Do not report in the following cases:
- The `null`/loose-comparison case is already ruled out by an earlier `if`/type check
  in the same function
- The coercion is deliberate, validated normalization documented at the call site

#### Thread Safety and Shared Process State
Only flag issues when the diff or surrounding file shows evidence of concurrent
worker/request execution against the same state:
- A session lock held across slow network, database, or CPU work when concurrent
  requests for the same session must proceed
- Static or singleton state mutated across requests in a long-running process
  (Swoole, RoadRunner, FPM with persistent workers) without synchronization
- A `foreach` value iterated by reference and reused without `unset()`, leaving it
  aliased to the final element and letting a later assignment corrupt the array

Do not report in the following cases:
- A traditional PHP-FPM request lifecycle with no persistent worker state — each
  request gets a fresh process/interpreter state
- Local variables within a function, never shared across requests
- The reference is `unset()` immediately after the loop

#### Injection (SQL, XSS, and Unsafe Deserialization)
- SQL assembled from untrusted values instead of parameter binding (identifiers such
  as column names or sort direction require an allowlist, since they cannot be bound)
- Untrusted output rendered without context-appropriate escaping for HTML text,
  attributes, URLs, or JavaScript; for `.phtml` templates, check whether a view helper
  already escapes the value
- `unserialize()` called on attacker-controlled data; `allowed_classes` narrows but
  does not eliminate the risk of untrusted data
- `eval`, dynamic `include`/`require`, or a shell command built through concatenation
  reached by untrusted input without a strict allowlist

Do not report in the following cases:
- The value is a literal constant, or is validated/escaped immediately before use by a
  function whose body is visible in the diff or surrounding file
- The framework's auto-escaping is active and the output is not explicitly marked raw

#### Resource Leaks
- Transactions, locks, or database cursors in a long-running process not committed,
  rolled back, or released on every reachable path, including an exception path
- A database transaction with an early return or exception path that can leave the
  transaction open
- cURL or stream operations lacking a timeout on a request path where a remote
  endpoint can stall execution

Do not report in the following cases:
- An ordinary request-scoped file or stream handle that PHP releases at request
  shutdown in a traditional FPM lifecycle
- The resource is owned by a framework or dependency-injection container that
  guarantees its release

#### Swallowed Errors
- A `catch (Throwable)`/`catch (Exception)` block that discards the failure, converts
  it into success, or replaces it with a misleading default on a path where the
  failure matters
- Warnings or errors suppressed with `@` where suppression can turn a meaningful
  failure into invalid state
- Cleanup, rollback, or response-finalization code that hides the primary exception

Do not report in the following cases:
- The `catch` block re-throws, logs at an appropriate level, or returns an explicit
  error result the caller checks
- A narrowly documented, safely-checked compatibility probe using `@` at a single line
