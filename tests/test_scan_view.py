from __future__ import annotations

import json
from pathlib import Path

from qagent.scan_view import endpoint_rows, scan_summary
from qagent.spec import load_spec


def test_rows_for_petstore(petstore_path: Path) -> None:
    rows = endpoint_rows(load_spec(petstore_path, strict=False))
    assert rows == [
        ("GET", "/pets", "-", "200, default", "List all pets"),
        ("POST", "/pets", "required", "201, 422", "Create a pet"),
        ("GET", "/pets/{petId}", "required", "200, 404", "Get one pet"),
        ("DELETE", "/pets/{petId}", "required", "204, 404", "[deprecated] Delete a pet"),
    ]


def test_optional_auth_and_operation_id_fallback(minibank_path: Path) -> None:
    rows = {(r[0], r[1]): r for r in endpoint_rows(load_spec(minibank_path, strict=False))}
    assert rows[("PATCH", "/users/{id}")][2] == "optional"
    assert rows[("GET", "/users/{id}")][4] == "getUser"


def test_summary_is_json_serializable(petstore_path: Path) -> None:
    summary = scan_summary(load_spec(petstore_path, strict=False))
    assert summary["endpoint_count"] == 4
    first = summary["endpoints"][0]
    assert first["method"] == "GET" and first["requires_auth"] is False
    json.dumps(summary)
