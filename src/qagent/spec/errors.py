"""Errors raised while reading an API spec. All carry a user-friendly message."""


class SpecError(Exception):
    """Base class for every problem with an input spec."""


class SpecLoadError(SpecError):
    """The spec could not be read or parsed (missing file, bad YAML, HTTP error)."""


class SpecValidationError(SpecError):
    """The document was read, but it is not a valid OpenAPI 3.x spec."""


class RefResolutionError(SpecError):
    """A ``$ref`` points somewhere that does not exist or is not supported."""
