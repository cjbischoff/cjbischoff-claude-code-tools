"""Proof by execution: the one lane where the harness runs target-derived code.

Every other phase reads the target and never runs it. This module reverses that
invariant, and only here. It runs when ``scan_options.prove_findings`` is true in
``kb/scan-profile.json``; the key is absent by default, so a normal audit never
executes anything. All building and running happen out of tree, under
``ws.repro``, so the target working tree stays untouched.

A proof promotes a finding to ``confirmed`` only when the agent drove a real
entrypoint (``scope: entrypoint``), the class has a wrapper-decidable oracle, and
the oracle observed the effect. Anything weaker records a degradation and leaves
the finding where it was.
"""

from __future__ import annotations

import json
import shutil
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sec_overlay.evidence import REPRODUCTION_RECEIPT, is_reproduction_receipt
from sec_overlay.workspace import Workspace

# Classes whose oracle a wrapper can decide without provisioning a live service.
AUTO_CONFIRMABLE = frozenset(
    {"ssrf", "cmdi", "path-traversal", "deserialization", "expr-eval-rce",
     "ssti", "injection"}
)

# Classes whose oracle needs a provisioned backend; these get a human-run harness.
HARNESS_ONLY = frozenset({"sqli", "authz"})

# Toolchains the lane can drive. Reported by preflight; never blocking.
PROVE_TOOLCHAINS = ("opa", "go", "node", "python3")

TOOLCHAIN_ABSENT = "prove: toolchain-absent"
SLICE_UNBUILDABLE = "prove: slice-unbuildable"
HARNESS_ROUTED = "prove: harness-only-class"
NOT_ORACLE_ABLE = "prove: class-not-oracle-able"
ORACLE_SILENT = "prove: oracle-silent"

_PROOF_FIELDS = (
    "command",
    "exit_code",
    "oracle",
    "oracle_result",
    "toolchain",
    "resolved_version",
    "scope",
)


def prove_enabled(ws: Workspace) -> bool:
    """Report whether the proof lane is switched on for this workspace.

    The lane is opt-in: it runs only when ``scan_options.prove_findings`` is
    exactly true. A missing, malformed, or silent profile leaves it off.

    Args:
        ws: The audit workspace.

    Returns:
        True when the lane may execute target-derived code.

    Example:
        >>> prove_enabled(ws)  # doctest: +SKIP
        False
    """
    path = ws.kb / "scan-profile.json"
    if not path.exists():
        return False
    try:
        options = json.loads(path.read_text()).get("scan_options") or {}
    except (json.JSONDecodeError, AttributeError):
        return False
    return options.get("prove_findings") is True


@dataclass
class Collector:
    """A loopback HTTP listener that records the paths it was asked for.

    Attributes:
        url: Base URL of the listener, e.g. ``http://127.0.0.1:54321``.
        paths: Request paths observed, in arrival order.
    """

    url: str
    paths: list[str] = field(default_factory=list)


@contextmanager
def loopback_collector() -> Iterator[Collector]:
    """Run an in-band oracle on loopback for the duration of a proof.

    The collector needs no egress: a proof points the target at ``collector.url``
    and a recorded path proves the request left the target.

    Yields:
        A :class:`Collector` whose ``paths`` fills as requests arrive.

    Example:
        >>> with loopback_collector() as c:  # doctest: +SKIP
        ...     run_the_proof(c.url)
    """
    paths: list[str] = []

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            paths.append(self.path)
            self.send_response(204)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            """Silence the default stderr access log."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield Collector(url=f"http://127.0.0.1:{server.server_port}", paths=paths)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _reject_reason(cls: str, proof: dict, which) -> str | None:
    """Return why this proof may not promote its finding, or None if it may."""
    if which(proof.get("toolchain") or "") is None:
        return TOOLCHAIN_ABSENT
    if proof.get("scope") != "entrypoint":
        return SLICE_UNBUILDABLE
    if cls in HARNESS_ONLY:
        return HARNESS_ROUTED
    if cls not in AUTO_CONFIRMABLE:
        return NOT_ORACLE_ABLE
    if proof.get("oracle_result") != "observed" or proof.get("exit_code") != 0:
        return ORACLE_SILENT
    return None


def _attach(data: dict, proof: dict) -> None:
    """Record the proof that ran on the finding, without promoting it."""
    data["reproduction"] = {k: proof.get(k) for k in _PROOF_FIELDS}


def _promote(data: dict) -> None:
    """Promote a finding on an entrypoint-driven, oracle-observed proof."""
    data["status"] = "confirmed"
    sources = list(data.get("evidence_sources") or [])
    if not any(is_reproduction_receipt(s) for s in sources):
        sources.append(REPRODUCTION_RECEIPT)
    data["evidence_sources"] = sources
    data["runtime_disposition"] = "static-settled"


def run_prove(ws: Workspace, target: str, *, which=shutil.which) -> dict:
    """Apply the agent's proposed proofs to the findings they name.

    Reads ``kb/prove.json``, decides each proof against the soundness rules, and
    writes the outcome back to the same file. A proof that ran attaches a
    ``reproduction`` object to its finding; only an entrypoint-driven proof of an
    oracle-able class promotes the finding to ``confirmed``.

    Args:
        ws: The audit workspace.
        target: The target root, recorded for the operator's audit trail.
        which: Injectable toolchain resolver.

    Returns:
        ``{enabled, target, proofs, promoted, degraded}``. ``degraded`` entries
        carry ``finding_id`` and ``reason``.

    Example:
        >>> run_prove(ws, "/src/app")["promoted"]  # doctest: +SKIP
        ['F-0100']
    """
    if not prove_enabled(ws):
        return {"enabled": False, "target": target, "proofs": [], "promoted": [], "degraded": []}
    ws.repro.mkdir(parents=True, exist_ok=True)
    path = ws.kb / "prove.json"
    try:
        proofs = json.loads(path.read_text()).get("proofs") or []
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        proofs = []
    promoted: list[str] = []
    degraded: list[dict] = []
    for proof in proofs:
        if not isinstance(proof, dict):
            continue
        finding_path = ws.findings_dir / f"{proof.get('finding_id')}.json"
        if not finding_path.exists():
            continue
        data = json.loads(finding_path.read_text())
        reason = _reject_reason(str(data.get("cls") or ""), proof, which)
        if reason != TOOLCHAIN_ABSENT:
            _attach(data, proof)
        if reason is None:
            _promote(data)
            promoted.append(data["id"])
        else:
            degraded.append({"finding_id": data["id"], "reason": reason})
        finding_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    result = {
        "enabled": True,
        "target": target,
        "proofs": proofs,
        "promoted": promoted,
        "degraded": degraded,
    }
    path.write_text(json.dumps(result, indent=2) + "\n")
    return result
