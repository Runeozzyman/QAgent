"""Command-line interface: `qagent ...`."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from qagent import __version__
from qagent.scan_view import SCAN_COLUMNS, endpoint_rows, scan_summary
from qagent.spec import SpecError, load_spec

app = typer.Typer(
    name="qagent",
    help="Autonomous QA agent: generate and run API tests from an OpenAPI spec.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

_METHOD_STYLES = {
    "GET": "green",
    "POST": "yellow",
    "PUT": "blue",
    "PATCH": "cyan",
    "DELETE": "red",
}


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"qagent {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show the version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """QAgent command-line tool."""


@app.command()
def scan(
    source: Annotated[
        str,
        typer.Argument(help="Path or URL of an OpenAPI 3.x spec (YAML or JSON)."),
    ],
    as_json: Annotated[
        bool, typer.Option("--json", help="Print a machine-readable summary instead of a table.")
    ] = False,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict/--no-strict",
            help="Run full OpenAPI validation (use --no-strict for slightly off specs).",
        ),
    ] = True,
) -> None:
    """Read a spec and list every endpoint QAgent can test."""
    try:
        spec = load_spec(source, strict=strict)
    except SpecError as exc:
        err_console.print(f"[bold red]Error:[/] {escape(str(exc))}")
        raise typer.Exit(code=1) from exc

    if as_json:
        typer.echo(json.dumps(scan_summary(spec), indent=2))
        return

    count = len(spec.endpoints)
    console.print(
        f"[bold]{escape(spec.title)}[/] v{escape(spec.version)} "
        f"[dim](OpenAPI {spec.openapi_version})[/] - {count} endpoint{'s' if count != 1 else ''}"
    )
    if spec.servers:
        console.print(f"[dim]Servers: {', '.join(spec.servers)}[/]")

    table = Table(show_lines=False, header_style="bold")
    for column in SCAN_COLUMNS:
        table.add_column(column, overflow="fold")
    for method, *rest in endpoint_rows(spec):
        style = _METHOD_STYLES.get(method, "white")
        # Escape so text like "[deprecated]" isn't read as Rich markup.
        table.add_row(f"[{style}]{method}[/]", *(escape(cell) for cell in rest))
    console.print(table)
