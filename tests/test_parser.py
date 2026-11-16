from __future__ import annotations

from pathlib import Path

import pytest

from qagent.models import ApiSpec
from qagent.spec import load_spec
from qagent.spec.refs import CIRCULAR_MARKER


@pytest.fixture
def petstore(petstore_path: Path) -> ApiSpec:
    return load_spec(petstore_path, strict=False)


@pytest.fixture
def minibank(minibank_path: Path) -> ApiSpec:
    return load_spec(minibank_path, strict=False)


def test_metadata(petstore: ApiSpec) -> None:
    assert petstore.title == "Petstore"
    assert petstore.version == "1.0.0"
    assert petstore.openapi_version == "3.0.3"
    assert petstore.servers == ["http://localhost:8080/v1"]
    assert "apiKey" in petstore.security_schemes


def test_lists_every_endpoint_sorted(petstore: ApiSpec) -> None:
    assert [e.key for e in petstore.endpoints] == [
        "GET /pets",
        "POST /pets",
        "GET /pets/{petId}",
        "DELETE /pets/{petId}",
    ]


def test_path_level_parameters_are_inherited(petstore: ApiSpec) -> None:
    endpoint = petstore.get("delete", "/pets/{petId}")
    assert endpoint is not None
    [param] = endpoint.params_in("path")
    assert param.name == "petId"
    assert param.required
    assert param.schema_ == {"type": "integer"}


def test_operation_parameter_overrides_path_level(minibank: ApiSpec) -> None:
    endpoint = minibank.get("GET", "/users/{id}")
    assert endpoint is not None
    [header] = endpoint.params_in("header")
    assert header.description == "operation level"
    assert header.required
    # The PATCH has no override, so it keeps the path-level version.
    patch = minibank.get("PATCH", "/users/{id}")
    assert patch is not None
    assert patch.params_in("header")[0].description == "path level"


def test_query_parameter(petstore: ApiSpec) -> None:
    endpoint = petstore.get("GET", "/pets")
    assert endpoint is not None
    [limit] = endpoint.params_in("query")
    assert limit.name == "limit"
    assert not limit.required
    assert limit.schema_["maximum"] == 100


def test_request_body_schema_is_resolved(petstore: ApiSpec) -> None:
    endpoint = petstore.get("POST", "/pets")
    assert endpoint is not None and endpoint.request_body is not None
    assert endpoint.request_body.required
    schema = endpoint.request_body.json_schema
    assert schema is not None
    assert schema["required"] == ["name"]
    assert "$ref" not in str(schema)


def test_vendor_json_media_type_counts_as_json(minibank: ApiSpec) -> None:
    endpoint = minibank.get("PATCH", "/users/{id}")
    assert endpoint is not None and endpoint.request_body is not None
    schema = endpoint.request_body.json_schema
    assert schema is not None
    # Sibling `description` next to $ref is kept (OpenAPI 3.1).
    assert schema["properties"]["email"] == {
        "type": "string",
        "format": "email",
        "description": "New email",
    }


def test_responses_resolved_and_ordered(petstore: ApiSpec) -> None:
    endpoint = petstore.get("GET", "/pets")
    assert endpoint is not None
    assert endpoint.status_codes == ["200", "default"]
    ok = endpoint.responses["200"].json_schema
    assert ok is not None and ok["type"] == "array"
    assert ok["items"]["allOf"][0]["required"] == ["name"]
    error = endpoint.responses["default"].json_schema
    assert error is not None and error["required"] == ["code", "message"]


def test_status_ranges_sort_between_codes_and_default(minibank: ApiSpec) -> None:
    endpoint = minibank.get("PATCH", "/users/{id}")
    assert endpoint is not None
    assert endpoint.status_codes == ["200", "4XX"]


def test_security_global_override_and_optional(petstore: ApiSpec, minibank: ApiSpec) -> None:
    list_pets = petstore.get("GET", "/pets")
    create_pet = petstore.get("POST", "/pets")
    assert list_pets is not None and create_pet is not None
    assert not list_pets.requires_auth  # `security: []` makes it public
    assert create_pet.requires_auth  # inherits the global apiKey requirement
    assert create_pet.security == [{"apiKey": []}]

    patch_user = minibank.get("PATCH", "/users/{id}")
    assert patch_user is not None
    assert patch_user.security  # has a requirement...
    assert not patch_user.requires_auth  # ...but `{}` makes it optional


def test_deprecated_and_operation_id(petstore: ApiSpec) -> None:
    endpoint = petstore.get("DELETE", "/pets/{petId}")
    assert endpoint is not None
    assert endpoint.deprecated
    assert endpoint.operation_id == "deletePet"
    assert endpoint.tags == ["pets"]


def test_recursive_schema_does_not_loop(minibank: ApiSpec) -> None:
    endpoint = minibank.get("GET", "/categories")
    assert endpoint is not None
    schema = endpoint.responses["200"].json_schema
    assert schema is not None
    assert schema["properties"]["children"]["items"][CIRCULAR_MARKER] is True


def test_get_returns_none_for_unknown(petstore: ApiSpec) -> None:
    assert petstore.get("PUT", "/pets") is None
