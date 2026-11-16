"""Resolve ``$ref`` pointers so the rest of QAgent never has to deal with them.

Only local references (``#/components/schemas/User``) are supported in v1.
Recursive schemas (a ``TreeNode`` whose ``children`` are ``TreeNode``s) are
handled by leaving the innermost repeat as a ``$ref`` marked with
``x-qagent-circular: true`` instead of expanding forever.
"""

from __future__ import annotations

import copy
from typing import Any

from qagent.spec.errors import RefResolutionError

CIRCULAR_MARKER = "x-qagent-circular"


def resolve_refs(document: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``document`` with every local ``$ref`` replaced by its target."""
    resolved = _resolve(document, document, stack=())
    assert isinstance(resolved, dict)
    return resolved


def resolve_pointer(document: dict[str, Any], ref: str) -> Any:
    """Look up a local JSON pointer such as ``#/components/schemas/User``."""
    if not ref.startswith("#"):
        raise RefResolutionError(
            f"External reference {ref!r} is not supported yet. "
            "Bundle the spec into a single file first "
            "(for example with `redocly bundle`)."
        )
    pointer = ref[1:]
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise RefResolutionError(f"Invalid JSON pointer in $ref {ref!r}.")

    node: Any = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        else:
            raise RefResolutionError(f"$ref {ref!r} points to something that does not exist.")
    return node


def _resolve(node: Any, document: dict[str, Any], stack: tuple[str, ...]) -> Any:
    if isinstance(node, list):
        return [_resolve(item, document, stack) for item in node]
    if not isinstance(node, dict):
        return node

    ref = node.get("$ref")
    if isinstance(ref, str):
        if ref in stack:
            return {"$ref": ref, CIRCULAR_MARKER: True}
        target = _resolve(resolve_pointer(document, ref), document, (*stack, ref))
        siblings = {k: v for k, v in node.items() if k != "$ref"}
        if not siblings:
            # Copy so two places that use the same component never share one object.
            return copy.deepcopy(target)
        if not isinstance(target, dict):
            raise RefResolutionError(
                f"$ref {ref!r} has sibling keys but does not point to an object."
            )
        # OpenAPI 3.1 allows keys next to $ref (e.g. a description override).
        merged = copy.deepcopy(target)
        merged.update(_resolve(siblings, document, stack))
        return merged

    return {key: _resolve(value, document, stack) for key, value in node.items()}
