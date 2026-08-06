# -*- coding: utf-8 -*-
"""Security tests for SurrealQL injection hardening in the repository layer."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from open_notebook.database.repository import (
    _ensure_safe_identifier,
    ensure_record_id,
)


class TestEnsureSafeIdentifier:
    def test_valid_identifiers(self):
        for name in ["source", "note", "has_source", "belongs_to", "_internal", "s2"]:
            assert _ensure_safe_identifier(name, "table") == name

    def test_rejects_injection(self):
        bad = [
            "source; DROP TABLE users; --",
            "note}->note",
            'table" ON DUPLICATE KEY',
            "x->y",
            "a b",
            "",
            "1table",
            "table; SELECT * FROM secrets;",
        ]
        for name in bad:
            with pytest.raises(ValueError):
                _ensure_safe_identifier(name, "table")

    def test_rejects_non_string(self):
        with pytest.raises(ValueError):
            _ensure_safe_identifier(123, "table")  # type: ignore[arg-type]


class TestEnsureRecordId:
    def test_roundtrip(self):
        rid = ensure_record_id("source:abc123")
        assert str(rid).endswith("abc123")

    def test_record_id_passthrough(self):
        rid = ensure_record_id("note:xyz")
        assert ensure_record_id(rid) == rid
