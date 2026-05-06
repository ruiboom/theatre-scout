from __future__ import annotations

import typer

from scout import __version__

app = typer.Typer(
    help="Theatre Scout — local directory of London theatre shows.", no_args_is_help=True
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """Theatre Scout CLI."""
