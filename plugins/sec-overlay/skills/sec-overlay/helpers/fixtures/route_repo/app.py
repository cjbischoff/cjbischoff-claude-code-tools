"""Two Flask routes; one is a policy-evaluation endpoint."""

from flask import Flask, request

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return {"ok": True}


@app.route("/policy/evaluate", methods=["POST"])
def evaluate():
    return {"allow": _evaluate(request.json["policy"])}


def _evaluate(policy_text: str) -> bool:
    raise NotImplementedError
