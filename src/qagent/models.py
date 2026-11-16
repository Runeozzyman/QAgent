"""Core data models.

These models are deliberately independent of OpenAPI: the parser in
``qagent.spec`` translates an OpenAPI document into them, and the rest of
QAgent (generators, runner, reports) only ever sees these types. A future
parser (for example, one that infers endpoints from recorded traffic) only
needs to produce the same models.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

HttpMethod = Literal["GET", "PUT", "POST", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"]
ParameterLocation = Literal["path", "query", "header", "cookie"]

JsonSchema = dict[str, Any]

#: Order used when sorting endpoints that share a path.
METHOD_ORDER: tuple[HttpMethod, ...] = (
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
    "TRACE",
)


class Parameter(BaseModel):
    """A path, query, header or cookie parameter."""

    name: str
    location: ParameterLocation
    required: bool = False
    schema_: JsonSchema = Field(default_factory=dict, alias="schema")
    description: str | None = None

    model_config = {"populate_by_name": True}


class RequestBody(BaseModel):
    """A request body, keyed by media type (e.g. ``application/json``)."""

    required: bool = False
    content: dict[str, JsonSchema] = Field(default_factory=dict)
    description: str | None = None

    @property
    def json_schema(self) -> JsonSchema | None:
        """The schema for a JSON body, if the endpoint accepts one."""
        return _json_schema_from(self.content)


class ResponseSpec(BaseModel):
    """A documented response for one status code (``"200"``, ``"4XX"``, ``"default"``)."""

    status: str
    description: str | None = None
    content: dict[str, JsonSchema] = Field(default_factory=dict)

    @property
    def json_schema(self) -> JsonSchema | None:
        return _json_schema_from(self.content)


class Endpoint(BaseModel):
    """One operation: an HTTP method on a path."""

    method: HttpMethod
    path: str
    operation_id: str | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    parameters: list[Parameter] = Field(default_factory=list)
    request_body: RequestBody | None = None
    responses: dict[str, ResponseSpec] = Field(default_factory=dict)
    #: Alternative security requirements; any one of them satisfies the endpoint.
    #: Each maps a security scheme name to its required scopes.
    security: list[dict[str, list[str]]] = Field(default_factory=list)
    deprecated: bool = False

    @property
    def key(self) -> str:
        """A stable, human-readable identifier such as ``"POST /users"``."""
        return f"{self.method} {self.path}"

    @property
    def requires_auth(self) -> bool:
        """True if every alternative security requirement needs credentials.

        An empty requirement (``{}``) in the list means auth is optional.
        """
        return bool(self.security) and all(self.security)

    @property
    def status_codes(self) -> list[str]:
        return sorted(self.responses, key=_status_sort_key)

    def params_in(self, location: ParameterLocation) -> list[Parameter]:
        return [p for p in self.parameters if p.location == location]


class ApiSpec(BaseModel):
    """A whole API: metadata plus every endpoint."""

    title: str
    version: str
    openapi_version: str
    description: str | None = None
    servers: list[str] = Field(default_factory=list)
    security_schemes: dict[str, JsonSchema] = Field(default_factory=dict)
    endpoints: list[Endpoint] = Field(default_factory=list)

    def get(self, method: str, path: str) -> Endpoint | None:
        method = method.upper()
        return next((e for e in self.endpoints if e.method == method and e.path == path), None)


def _json_schema_from(content: dict[str, JsonSchema]) -> JsonSchema | None:
    for media_type, schema in content.items():
        base = media_type.split(";", 1)[0].strip().lower()
        if base == "application/json" or base.endswith("+json"):
            return schema
    return None


def _status_sort_key(status: str) -> tuple[int, str]:
    # Numeric codes first ("200" < "404"), then ranges ("4XX"), then "default".
    if status.isdigit():
        return (0, status)
    if status.lower() == "default":
        return (2, status)
    return (1, status)
