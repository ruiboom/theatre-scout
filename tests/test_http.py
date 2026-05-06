from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from scout.http import USER_AGENT, Cache, Client, RateLimiter, is_allowed


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


def test_cache_miss_then_hit(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    assert cache.get("https://almeida.co.uk/whats-on") is None
    cache.put("https://almeida.co.uk/whats-on", b"<html>hi</html>")
    assert cache.get("https://almeida.co.uk/whats-on") == b"<html>hi</html>"


def test_is_allowed_respects_disallow() -> None:
    robots = "User-agent: *\nDisallow: /admin/\n"
    assert is_allowed("https://example.com/whats-on", robots) is True
    assert is_allowed("https://example.com/admin/secrets", robots) is False


def test_is_allowed_no_robots_returns_true() -> None:
    assert is_allowed("https://example.com/anything", None) is True


def _mock_transport(responses: dict[str, tuple[int, bytes]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url in responses:
            status, body = responses[url]
            return httpx.Response(status, content=body)
        return httpx.Response(404, content=b"")

    return httpx.MockTransport(handler)


def test_client_get_returns_response_and_caches(tmp_path: Path) -> None:
    transport = _mock_transport({"https://almeida.co.uk/whats-on": (200, b"<html>1</html>")})
    cache = Cache(tmp_path)
    client = Client(
        http=httpx.Client(transport=transport),
        rate_limiter=RateLimiter(min_interval=0.0),
        cache=cache,
        fetch_robots=lambda host: None,
    )
    r1 = client.get("https://almeida.co.uk/whats-on")
    assert r1 is not None and r1.content == b"<html>1</html>"

    transport2 = _mock_transport({})
    client._http = httpx.Client(transport=transport2)
    r2 = client.get("https://almeida.co.uk/whats-on")
    assert r2 is not None and r2.content == b"<html>1</html>"


def test_client_get_blocked_by_robots_returns_none(tmp_path: Path) -> None:
    transport = _mock_transport({"https://example.com/admin/x": (200, b"x")})
    client = Client(
        http=httpx.Client(transport=transport),
        rate_limiter=RateLimiter(min_interval=0.0),
        cache=Cache(tmp_path),
        fetch_robots=lambda host: "User-agent: *\nDisallow: /admin/\n",
    )
    assert client.get("https://example.com/admin/x") is None


def test_client_get_sets_user_agent(tmp_path: Path) -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, content=b"ok")

    client = Client(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        rate_limiter=RateLimiter(min_interval=0.0),
        cache=Cache(tmp_path),
        fetch_robots=lambda host: None,
    )
    client.get("https://example.com/")
    assert seen["ua"] == USER_AGENT


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Safety net: fail loudly if a test reaches the real network."""

    def boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("Real network call blocked in tests")

    monkeypatch.setattr("socket.socket", boom)
