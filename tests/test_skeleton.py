from typer.testing import CliRunner

from scout import __version__
from scout.cli import app


def test_package_imports() -> None:
    assert __version__ == "0.1.0"


def test_cli_version_runs() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
