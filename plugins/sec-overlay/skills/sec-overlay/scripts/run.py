#!/usr/bin/env python3
"""Entry point for the sec-overlay skill.

Placeholder — actual check logic is not implemented yet.

Args:
    target (optional positional): path or git diff range to check.
        Defaults to the current working tree.

Output:
    One line per finding: <file>:<line> <rule-id> <message>
    Exit code 0 when the run completes, regardless of finding count.
"""

import sys


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"sec-overlay: no checks implemented yet (target: {target})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
