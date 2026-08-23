> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear. Adapted from open-code-review (Apache-2.0).

#### Null-Pointer Dereference and Uninitialized Pointers
- A pointer returned by `malloc`/`calloc`/`realloc`/`fopen`/`strdup` or a lookup
  function dereferenced without a NULL check on the path in the diff
- A pointer read or dereferenced before it is assigned a value, or after it was
  freed and not reset to NULL (dangling pointer, use-after-free)
- A pointer passed to a function and used as non-null without the callee's contract
  guaranteeing non-null input

Do not report in the following cases:
- The pointer is checked for NULL earlier in the same function with no intervening
  reassignment
- The pointer is the address of a stack/global variable, which is never NULL

#### Thread Safety and Data Races
Only flag when the diff or surrounding file shows evidence of threads, signal
handlers, or async callbacks touching the same state:
- A global or static variable read and written from more than one thread without a
  mutex, atomic type, or equivalent synchronization
- A check-then-act sequence (`if (!initialized) { init(); }`) on shared state with no
  lock, allowing two threads to both pass the check
- A `pthread_mutex_t` locked but not unlocked on an error or early-return path

Do not report in the following cases:
- The variable is thread-local (`__thread`/`_Thread_local`) or only ever touched from
  a single thread in the visible code
- The code already wraps the shared access in a lock consistently

#### Injection: Command, Format-String, and Unbounded Copies
- Untrusted input passed as the format argument to `printf`/`fprintf`/`syslog`
  (`printf(user_input)` instead of `printf("%s", user_input)`)
- Untrusted input concatenated into a command string passed to `system`, `popen`,
  or `exec*` without validation or an allowlist
- `strcpy`, `strcat`, `sprintf`, or `gets` used on a fixed-size buffer with
  attacker-influenced or unbounded-length input

Do not report in the following cases:
- The format string is a literal constant and the untrusted value is passed as an
  argument, not as the format itself
- The bounded variants (`strncpy`, `strncat`, `snprintf`) are used with a size
  derived from the destination buffer

#### Resource Leaks
- `malloc`/`calloc`/`realloc`, `fopen`, `open`, or `socket` whose handle is not
  freed/closed on every reachable path, including error and early-return paths
- A reallocation (`ptr = realloc(ptr, n)`) that overwrites the original pointer
  without checking for `NULL`, leaking the original allocation on failure
- A lock acquired (`pthread_mutex_lock`) with no matching unlock on an error path

Do not report in the following cases:
- The allocation's lifetime is intentionally the process lifetime (freed by
  process exit, documented as such)
- The resource is already released via a `goto cleanup`/`goto fail` pattern the
  function consistently uses

#### Ignored Return Values and Error Handling
- The return value of `malloc`, `read`, `write`, `fread`, `fwrite`, `fclose`, or a
  syscall is not checked before the result is used or assumed successful
- `errno` set by a failed call is neither read nor cleared before the next call
  that might rely on it
- A partial `read`/`write` (fewer bytes than requested) treated as if it fully
  succeeded

Do not report in the following cases:
- The return value is explicitly discarded with a documented reason (e.g. `close`
  on a best-effort cleanup path) and failure there has no correctness impact
- The call cannot fail for the inputs given, per the standard's documented contract
