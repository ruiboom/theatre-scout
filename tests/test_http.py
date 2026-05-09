from __future__ import annotations

import socket
from pathlib import Path

import pytest

from scout.http import Client, RateLimiter, Response, is_allowed


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


def test_rate_limiter_waits_within_host() -> None:
    clock = FakeClock()
    rl = RateLimiter(min_interval=1.0, now=clock.now, sleep=clock.sleep)
    rl.wait_for("almeida.co.uk")
    assert clock.slept == []
    rl.wait_for("almeida.co.uk")
    assert clock.slept == [1.0]


def test_rate_limiter_independent_across_hosts() -> None:
    clock = FakeClock()
    rl = RateLimiter(min_interval=1.0, now=clock.now, sleep=clock.sleep)
    rl.wait_for("almeida.co.uk")
    rl.wait_for("bushtheatre.co.uk")
    assert clock.slept == []


def test_rate_limiter_no_wait_after_enough_time() -> None:
    clock = FakeClock()
    rl = RateLimiter(min_interval=1.0, now=clock.now, sleep=clock.sleep)
    rl.wait_for("almeida.co.uk")
    clock.t = 5.0
    rl.wait_for("almeida.co.uk")
    assert clock.slept == []


def test_is_allowed_respects_disallow() -> None:
    robots = "User-agent: *\nDisallow: /admin/\n"
    assert is_allowed("https://example.com/whats-on", robots) is True
    assert is_allowed("https://example.com/admin/secrets", robots) is False


def test_is_allowed_no_robots_returns_true() -> None:
    assert is_allowed("https://example.com/anything", None) is True


def _make_client(
    *,
    fetch_fn=None,  # type: ignore[no-untyped-def]
    stealth_fetch_fn=None,  # type: ignore[no-untyped-def]
    fetch_robots=lambda host: None,
):
    return Client(
        rate_limiter=RateLimiter(min_interval=0.0),
        fetch_fn=fetch_fn or (lambda url: Response(url=url, status_code=200, content=b"hi")),
        stealth_fetch_fn=stealth_fetch_fn
        or (lambda url: Response(url=url, status_code=200, content=b"hi-stealth")),
        fetch_robots=fetch_robots,
    )


def test_client_get_uses_fast_path_by_default() -> None:
    seen: dict[str, str] = {}

    def fetch(url: str) -> Response:
        seen["mode"] = "fast"
        return Response(url=url, status_code=200, content=b"f")

    def stealth(url: str) -> Response:
        seen["mode"] = "stealth"
        return Response(url=url, status_code=200, content=b"s")

    client = _make_client(fetch_fn=fetch, stealth_fetch_fn=stealth)
    r = client.get("https://example.com/")
    assert r is not None and r.content == b"f"
    assert seen["mode"] == "fast"


def test_client_get_routes_stealth_when_flag_true() -> None:
    seen: dict[str, str] = {}

    def fetch(url: str) -> Response:
        seen["mode"] = "fast"
        return Response(url=url, status_code=200, content=b"f")

    def stealth(url: str) -> Response:
        seen["mode"] = "stealth"
        return Response(url=url, status_code=200, content=b"s")

    client = _make_client(fetch_fn=fetch, stealth_fetch_fn=stealth)
    r = client.get("https://example.com/", stealth=True)
    assert r is not None and r.content == b"s"
    assert seen["mode"] == "stealth"


def test_client_get_blocked_by_robots_returns_none() -> None:
    client = _make_client(fetch_robots=lambda host: "User-agent: *\nDisallow: /admin/\n")
    assert client.get("https://example.com/admin/x") is None


def test_client_robots_failure_does_not_break_fetch() -> None:
    def boom(host: str) -> str | None:
        raise RuntimeError("dns down")

    client = _make_client(fetch_robots=boom)
    r = client.get("https://example.com/")
    assert r is not None and r.status_code == 200


def test_rate_limiter_concurrent_same_host_serializes() -> None:
    """Two threads hitting the same host should observe the per-host gap."""
    import threading
    import time

    rl = RateLimiter(min_interval=0.05)
    times: list[float] = []
    barrier = threading.Barrier(2)

    def worker() -> None:
        barrier.wait()  # release both threads at once
        rl.wait_for("example.com")
        times.append(time.monotonic())

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    delta = abs(times[1] - times[0])
    assert delta >= 0.04, f"expected ≥ 40ms gap on same host, got {delta * 1000:.1f}ms"


def test_rate_limiter_concurrent_different_hosts_parallel() -> None:
    """Two threads on different hosts should NOT block each other."""
    import threading
    import time

    rl = RateLimiter(min_interval=0.5)
    rl.wait_for("a.example.com")  # prime so next call to a.* would wait
    rl.wait_for("b.example.com")  # prime so next call to b.* would wait

    start = time.monotonic()
    threads = [
        threading.Thread(target=rl.wait_for, args=("a.example.com",)),
        threading.Thread(target=rl.wait_for, args=("b.example.com",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start
    # Each host individually waits ~0.5s; in parallel total should be ~0.5s, not 1s.
    assert elapsed < 0.85, f"expected ~0.5s parallel, got {elapsed:.2f}s"


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Safety net: any test that reaches a real socket fails loudly."""

    def boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("Real network call blocked in tests")

    monkeypatch.setattr(socket, "socket", boom)
