"""ast-grep structural-search backend.

Structural AST pattern search across languages, offline, no build. Used as a
tool-grounded gate signal (precise sink/sanitizer/caller detection), the
mechanical hypothesis-test tool the agents run, and the structural sibling-sweep.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def astgrep_available(*, which=shutil.which) -> bool:
    """Return True if the ast-grep binary (``ast-grep`` or ``sg``) is on PATH."""
    return which("ast-grep") is not None or which("sg") is not None


def _binary(which=shutil.which) -> str:
    """Resolve the ast-grep binary name (prefer ``ast-grep``)."""
    return "ast-grep" if which("ast-grep") is not None else "sg"


def parse_astgrep_json(payload: list) -> list[dict]:
    """Convert ast-grep ``--json`` output to ``[{file, line, text}]``.

    Args:
        payload: Parsed ast-grep JSON (a list of match objects).

    Returns:
        Matches with 1-indexed line numbers (ast-grep reports 0-indexed).
    """
    out: list[dict] = []
    for m in payload:
        line0 = m.get("range", {}).get("start", {}).get("line", 0)
        out.append({"file": m.get("file", ""), "line": line0 + 1, "text": m.get("text", "")})
    return out


def run_astgrep(pattern: str, lang: str, root: str, *, runner=subprocess.run) -> list[dict]:
    """Run an ast-grep structural pattern search.

    Args:
        pattern: An ast-grep pattern (e.g. ``$CUR.execute($$$)``).
        lang: Language id (``python``, ``go``, ``javascript``, ...).
        root: Directory or file to search.
        runner: Injectable subprocess runner (for testing).

    Returns:
        Parsed matches ``[{file, line, text}]``; empty on non-JSON/empty output.
    """
    p = Path(root)
    is_file = p.is_file()
    if is_file:
        # ast-grep globs are gitignore-style and match at any depth, so a bare
        # basename could pull in siblings (e.g. foo/index.ts AND foo/bar/index.ts).
        # Scan the parent scoped by basename, then post-filter to the exact file.
        cmd = [_binary(), "run", "--pattern", pattern, "--lang", lang, "--json",
               "--globs", p.name, str(p.parent)]
    else:
        cmd = [_binary(), "run", "--pattern", pattern, "--lang", lang, "--json", root]
    completed = runner(cmd, capture_output=True, text=True, check=False)
    text = (completed.stdout or "").strip()
    if not text:
        return []
    try:
        matches = parse_astgrep_json(json.loads(text))
    except json.JSONDecodeError:
        return []
    if is_file:
        target = p.resolve()
        matches = [m for m in matches if Path(m["file"]).resolve() == target]
    return matches


def build_rule(
    pattern: str,
    lang: str,
    *,
    not_pattern: str | None = None,
    inside: str | None = None,
    rule_id: str = "sec-overlay-adhoc",
) -> str:
    """Build inline-rule YAML for a relational ast-grep query.

    A plain pattern cannot express an absence. This wraps a pattern in the
    relational form so a caller can ask for "this construction, but NOT
    containing that option" — the structural half of the absence idiom.

    Args:
        pattern: The construction to match.
        lang: ast-grep language name (``go``, ``python``, ``typescript``, ...).
        not_pattern: When given, a match is kept only if this pattern is absent
            from anywhere inside it.
        inside: When given, a match is kept only if it sits inside this pattern.
        rule_id: Rule id, echoed in ast-grep's output.

    Returns:
        YAML text suitable for ``run_astgrep_rule``.

    Note:
        Go needs ``kind``/``has`` anchoring that this helper does not generate:
        a selector-call pattern such as ``rego.New($ARGS)`` matches nothing.
        For Go, write the rule by hand and pass it to ``run_astgrep_rule``
        directly, or through the ``rule --file`` CLI subcommand.
    """
    lines = [f"id: {rule_id}", f"language: {lang}", "rule:"]
    if not_pattern is None and inside is None:
        lines.append(f"  pattern: {pattern}")
    else:
        lines.append("  all:")
        lines.append(f"    - pattern: {pattern}")
        if not_pattern is not None:
            lines.append("    - not:")
            lines.append("        has:")
            lines.append("          stopBy: end")
            lines.append(f"          pattern: {not_pattern}")
        if inside is not None:
            lines.append("    - inside:")
            lines.append("        stopBy: end")
            lines.append(f"        pattern: {inside}")
    lines.append("severity: warning")
    lines.append(f"message: {rule_id}")
    return "\n".join(lines) + "\n"


def run_astgrep_rule(yaml_text: str, root: str, *, runner=subprocess.run) -> list[dict]:
    """Run a relational ast-grep rule and return its matches.

    Args:
        yaml_text: Inline-rule YAML, from ``build_rule`` or written by hand.
        root: File or directory to scan.
        runner: Injection point for tests.

    Returns:
        Parsed matches ``[{file, line, text}]``; empty on non-JSON/empty output.
    """
    cmd = [_binary(), "scan", "--inline-rules", yaml_text, "--json", root]
    completed = runner(cmd, capture_output=True, text=True, check=False)
    text = (completed.stdout or "").strip()
    if not text:
        return []
    try:
        return parse_astgrep_json(json.loads(text))
    except json.JSONDecodeError:
        return []


def main(argv: list[str] | None = None) -> int:
    """CLI: run an ast-grep pattern and print ``file:line\\ttext`` per match."""
    parser = argparse.ArgumentParser(prog="sec-overlay-astgrep")
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="Structural pattern search.")
    r.add_argument("--pattern", required=True)
    r.add_argument("--lang", required=True)
    r.add_argument("--root", required=True)
    r.add_argument("--not", dest="not_pattern", default=None,
                    help="Keep a match only when this pattern is absent from it.")
    q = sub.add_parser("rule", help="Run a hand-written inline rule file.")
    q.add_argument("--file", required=True)
    q.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "run":
        if args.not_pattern:
            matches = run_astgrep_rule(
                build_rule(args.pattern, args.lang, not_pattern=args.not_pattern), args.root
            )
        else:
            matches = run_astgrep(args.pattern, args.lang, args.root)
        for m in matches:
            print(f"{m['file']}:{m['line']}\t{m['text']}")
        return 0
    if args.cmd == "rule":
        for m in run_astgrep_rule(Path(args.file).read_text(), args.root):
            print(f"{m['file']}:{m['line']}\t{m['text']}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
