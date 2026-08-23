> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear. Adapted from open-code-review (Apache-2.0).

#### Null and Empty-Optional Dereference
- A raw pointer, `std::optional`, or smart pointer dereferenced (`*`, `->`, `.value()`
  without a `has_value()`/truthiness check on the path in the diff
- A moved-from object (`std::move(x)` then later use of `x`) accessed as if it still
  holds its prior state, including a moved-from smart pointer used as non-null
- A `nullptr` default parameter or return value used by a caller without a guard

Do not report in the following cases:
- The optional/pointer is checked earlier in the same function with no intervening
  reassignment
- `.value()` is called after `has_value()` already returned true in the same branch

#### Thread Safety and Data Races
Only flag when the diff or surrounding file shows evidence of threads or async tasks:
- A shared container or variable read/written by more than one thread without a
  `std::mutex`, `std::atomic`, or equivalent synchronization primitive
- A `std::lock_guard`/`std::unique_lock` missing on a path that mutates state also
  guarded elsewhere in the same class, leaving inconsistent locking
- A double-checked-locking pattern without `std::atomic`/memory-order guarantees

Do not report in the following cases:
- The state is local to the function/thread with no evidence of sharing
- The container is already consistently guarded by the same mutex on every access

#### Injection: Command, Format-String, and Unbounded Copies
- Untrusted input passed as the format argument to C-style `printf` family calls, or
  concatenated into a command string passed to `system`/`popen`/`exec*`
- Legacy C string functions (`strcpy`, `sprintf`, `gets`) used on attacker-influenced
  input inside otherwise-modern C++ code
- A SQL query string built by concatenating untrusted input instead of a prepared
  statement/parameter binding API

Do not report in the following cases:
- The format string is a compile-time literal and untrusted data is passed only as
  an argument
- The value is validated or escaped immediately before use by a visible function

#### RAII and Resource Leaks
- `new` used to acquire a resource without a corresponding `std::unique_ptr`,
  `std::shared_ptr`, or matching `delete` on every path, including exception paths
- A file handle, socket, or lock acquired without a scoped-release idiom (RAII
  wrapper, `std::lock_guard`, destructor) and released manually with a path that can
  skip the release
- A `std::shared_ptr` cycle (e.g. two objects holding `shared_ptr` to each other)
  with no `std::weak_ptr` to break it, causing a leak

Do not report in the following cases:
- The raw pointer is non-owning (observer) and ownership is clearly held elsewhere
  via a smart pointer
- The resource is already released by an enclosing RAII wrapper visible in context

#### Swallowed Exceptions and Ignored Errors
- A `catch (...)` or a specific `catch` block that is empty or only logs without
  rethrowing, recovering, or otherwise handling the failure
- An exception's original cause discarded when wrapped and rethrown as a different
  type, with no `std::nested_exception`/inner-exception chaining
- A return code or `errno` from a C API called from C++ left unchecked before the
  result is used

Do not report in the following cases:
- The catch block performs a documented, intentional recovery (default value,
  logged-and-continue) appropriate to the call site
- The exception type is caught specifically to translate it into a documented error
  contract the caller checks
