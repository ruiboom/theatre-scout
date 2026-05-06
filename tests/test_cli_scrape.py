from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scout import cli, scraper
from scout.models import ScrapeRun

runner = CliRunner()


def _run(slug: str, status: str = "success", shows: int = 5) -> ScrapeRun:
    return ScrapeRun(
        theatre_slug=slug,
        started_at=datetime(2026, 5, 7, tzinfo=UTC),
        finished_at=datetime(2026, 5, 7, tzinfo=UTC),
        status=status,  # type: ignore[arg-type]
        shows_found=shows,
    )


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(cli, "DATA_DIR", tmp_path)


def test_scrape_all_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scraper, "run_all", lambda c, conn, **kw: [_run("almeida"), _run("bush")])
    result = runner.invoke(cli.app, ["scrape"])
    assert result.exit_code == 0, result.output
    assert "almeida" in result.output
    assert "bush" in result.output
    assert "success" in result.output


def test_scrape_all_failed_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scraper,
        "run_all",
        lambda c, conn, **kw: [_run("almeida", status="failed", shows=0)],
    )
    result = runner.invoke(cli.app, ["scrape"])
    assert result.exit_code == 1


def test_scrape_one_only_runs_one(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, str] = {}

    def fake_run_one(slug: str, client, conn, **kw):  # type: ignore[no-untyped-def]
        called["slug"] = slug
        return _run(slug)

    monkeypatch.setattr(scraper, "run_one", fake_run_one)
    result = runner.invoke(cli.app, ["scrape", "--theatre", "almeida"])
    assert result.exit_code == 0
    assert called == {"slug": "almeida"}


def test_list_command_shows_all_theatres() -> None:
    result = runner.invoke(cli.app, ["list"])
    assert result.exit_code == 0
    assert "almeida" in result.output
    assert "young-vic" in result.output
    assert "Almeida Theatre" in result.output
