"""Template rendering fixture: one unsandboxed environment, one sandboxed."""

from jinja2 import Environment
from jinja2.sandbox import SandboxedEnvironment


def render_unsafe(template_text: str, data: dict) -> str:
    """Unsandboxed: attribute traversal from the template reaches Python objects."""
    return Environment().from_string(template_text).render(**data)


def render_safe(template_text: str, data: dict) -> str:
    """Sandboxed: the environment blocks unsafe attribute access."""
    return SandboxedEnvironment().from_string(template_text).render(**data)
