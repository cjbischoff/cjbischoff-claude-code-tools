"""Tests for correlation manifest including DataChannel model."""

import json
from pathlib import Path

from sec_overlay.correlate.manifest import (
    ROLES,
    DataChannel,
    Member,
)


def test_roles_are_defined():
    assert "rbac-source" in ROLES
    assert "service-enforcer" in ROLES
    assert "infra" in ROLES


def test_member_fields():
    m = Member(slug="comply", repo_root="/repo/comply", scan_scope=".", role="infra")
    assert m.slug == "comply"
    assert m.member_key == "comply#."


def test_data_channel_fields():
    c = DataChannel(
        id="sources.feed_template",
        description="DB column: parsed OVAL XML",
        producer="enrichmentlibrarybuilder",
        consumer="comply",
        producer_site="vulndb.go:1073",
        consumer_site="normal.ts:69",
        medium="database",
    )
    assert c.id == "sources.feed_template"
    assert c.producer == "enrichmentlibrarybuilder"
    assert c.consumer == "comply"
    assert c.producer_site == "vulndb.go:1073"
    assert c.consumer_site == "normal.ts:69"
    assert c.medium == "database"


def test_data_channel_default_medium():
    c = DataChannel(
        id="test-channel",
        description="test",
        producer="a", consumer="b",
        producer_site="a.py:1", consumer_site="b.py:1",
    )
    assert c.medium == "database"
