"""Outbound-request fixture: one call with no timeout, one call that sets one."""

import requests


def fetch_unsafe(url: str) -> str:
    """No timeout: a slow or hostile endpoint holds the worker until the socket closes."""
    return requests.get(url).text


def fetch_safe(url: str) -> str:
    """A timeout bounds the wait, so the worker is released."""
    return requests.get(url, timeout=5).text
