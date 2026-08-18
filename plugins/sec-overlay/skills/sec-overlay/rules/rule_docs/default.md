#### Correctness
Is the logic correct? Are boundary conditions and error paths handled?
Is the change consistent with how the surrounding file already behaves?

#### Security
Are there injection risks (SQL, shell, template, deserialization)?
Is sensitive data (secrets, tokens, PII) handled and logged correctly?
Is access control or input validation missing at a trust boundary?

#### Resource Handling
Are files, sockets, locks, or connections released on every path, including errors?
Are exceptions caught, logged or re-raised, and never silently discarded?

#### Concurrency
Is shared mutable state accessed from more than one thread, process, or async task
without synchronization?

#### Maintainability
Is the change clear and consistent with the project's existing style and structure?
