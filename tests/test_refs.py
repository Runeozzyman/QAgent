from __future__ import annotations

from typing import Any

import pytest

from qagent.spec.errors import RefResolutionError
from qagent.spec.refs import CIRCULAR_MARKER, resolve_pointer, resolve_refs


def test_resolves_nested_refs() -> None:
    doc: dict[str, Any] = {
        "a": {"$ref": "#/defs/b"},
        "defs": {"b": {"inner": {"$ref": "#/defs/c"}}, "c": {"type": "string"}},
    }
    resolved = resolve_refs(doc)
    assert resolved["a"] == {"inner": {"type": "string"}}


def test_does_not_modify_input() -> None:
    doc: dict[str, Any] = {"a": {"$ref": "#/defs/b"}, "defs": {"b": {"type": "integer"}}}
    resolve_refs(doc)
    assert doc["a"] == {"$ref": "#/defs/b"}


def test_each_use_is_an_independent_copy() -> None:
    doc: dict[str, Any] = {
        "x": {"$ref": "#/defs/s"},
        "y": {"$ref": "#/defs/s"},
        "defs": {"s": {"type": "object"}},
    }
    resolved = resolve_refs(doc)
    resolved["x"]["type"] = "changed"
    assert resolved["y"]["type"] == "object"


def test_json_pointer_escapes() -> None:
    doc: dict[str, Any] = {"paths": {"/users/{id}": {"get": {"ok": True}}}, "a~b": 1}
    assert resolve_pointer(doc, "#/paths/~1users~1{id}/get") == {"ok": True}
    assert resolve_pointer(doc, "#/a~0b") == 1


def test_pointer_into_list() -> None:
    doc: dict[str, Any] = {"items": [{"n": 0}, {"n": 1}]}
    assert resolve_pointer(doc, "#/items/1") == {"n": 1}


def test_missing_target_raises() -> None:
    with pytest.raises(RefResolutionError, match="does not exist"):
        resolve_refs({"a": {"$ref": "#/nowhere"}})


def test_external_ref_is_explained() -> None:
    with pytest.raises(RefResolutionError, match="External reference"):
        resolve_refs({"a": {"$ref": "other.yaml#/User"}})


def test_circular_ref_is_cut_and_marked() -> None:
    doc: dict[str, Any] = {
        "root": {"$ref": "#/defs/Node"},
        "defs": {
            "Node": {
                "type": "object",
                "properties": {"children": {"type": "array", "items": {"$ref": "#/defs/Node"}}},
            }
        },
    }
    resolved = resolve_refs(doc)
    items = resolved["root"]["properties"]["children"]["items"]
    assert items == {"$ref": "#/defs/Node", CIRCULAR_MARKER: True}


def test_sibling_keys_override_target() -> None:
    doc: dict[str, Any] = {
        "a": {"$ref": "#/defs/s", "description": "override"},
        "defs": {"s": {"type": "string", "description": "original"}},
    }
    assert resolve_refs(doc)["a"] == {"type": "string", "description": "override"}
