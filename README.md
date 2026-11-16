# QAgent

Autonomous QA agent: point it at an OpenAPI spec and it generates and runs API tests.

> **Status:** work in progress. Phase 1 (reading specs) is done. Test generation and running come next.

## Install (development)

```bash
git clone https://github.com/Runeozzyman/QAgent.git
cd QAgent
uv sync                 # creates .venv with runtime + dev dependencies
uv run qagent --version
```

## Usage

### `qagent scan`

Read an OpenAPI 3.x spec from a file or URL and list every endpoint QAgent can test.

```bash
uv run qagent scan tests/fixtures/petstore.yaml
uv run qagent scan http://localhost:8000/openapi.json
uv run qagent scan openapi.yaml --json        # machine-readable output
uv run qagent scan openapi.yaml --no-strict   # skip full validation for slightly off specs
```

It prints the API title, version and endpoint count, then a table with one row per endpoint:
method, path, whether auth is required, documented status codes and summary.

## How it works

```
source (file / URL)
  → loader     read JSON or YAML                       qagent/spec/loader.py
  → validate   OpenAPI 3.x checks, friendly errors      qagent/spec/validate.py
  → refs       inline every local $ref                  qagent/spec/refs.py
  → parser     build Endpoint / ApiSpec models          qagent/spec/parser.py
```

The rest of QAgent only uses the models in `qagent/models.py`, which don't depend on OpenAPI.
Supporting another input format later only means writing a new parser.

Current limitations:

- Only local `$ref`s (`#/components/...`). Bundle multi-file specs first, e.g. `redocly bundle`.
- Recursive schemas are expanded once; the repeat is left as a `$ref` marked `x-qagent-circular`.
- Swagger 2.0 is rejected with a pointer to a converter.

## Development

```bash
uv run pytest          # tests
uv run ruff check .    # lint
uv run ruff format .   # format
uv run mypy            # type check (strict)
uv run pre-commit install
```

See the project roadmap for upcoming phases: demo API, test runner, LLM test generation, reports and a GitHub Action.
