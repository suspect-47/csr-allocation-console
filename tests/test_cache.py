"""you.com response cache: a second identical call is served from cache
(spec §2, §9 step 2 — the offline half; the live half is an integration test)."""

from __future__ import annotations

import pytest
from app import kv
from app.clients import youcom


@pytest.fixture(autouse=True)
def _fake_kv_and_key(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, dict[str, object]] = {}
    monkeypatch.setattr(kv, "cache_get", lambda key: store.get(key))
    monkeypatch.setattr(kv, "cache_set", lambda key, value: store.__setitem__(key, value))
    monkeypatch.setenv("YOU_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("YOU_RESEARCH_API_KEY", "test-key")


def _search_payload() -> dict[str, object]:
    # Mirrors the live /v1/search shape: results.web[] with description/snippets.
    return {"results": {"web": [{"title": "T", "url": "https://a.org", "description": "s"}]}, "metadata": {}}


def test_second_identical_search_hits_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fake_get(base_url: str, path: str, api_key: str, params: dict[str, object]) -> dict[str, object]:
        calls["n"] += 1
        return _search_payload()

    monkeypatch.setattr(youcom, "_get", fake_get)

    first = youcom.search("clean water Kenya", freshness="week", count=10)
    second = youcom.search("clean water Kenya", freshness="week", count=10)

    assert calls["n"] == 1                     # network hit once
    assert first.hits[0].url == "https://a.org"
    assert second.hits[0].url == "https://a.org"


def test_different_params_miss_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fake_get(base_url: str, path: str, api_key: str, params: dict[str, object]) -> dict[str, object]:
        calls["n"] += 1
        return {"results": {"web": []}, "metadata": {}}

    monkeypatch.setattr(youcom, "_get", fake_get)
    youcom.search("a", freshness="week")
    youcom.search("b", freshness="week")
    assert calls["n"] == 2


def test_research_cache_and_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fake_post(base_url: str, path: str, api_key: str, payload: dict[str, object]) -> dict[str, object]:
        calls["n"] += 1
        return {"output": {"content": "answer text", "content_type": "text",
                            "sources": [{"url": "https://s.org", "title": "S", "snippets": ["x"]}]}}

    monkeypatch.setattr(youcom, "_post", fake_post)
    first = youcom.research("does X exist?", effort="lite")
    second = youcom.research("does X exist?", effort="lite")
    assert calls["n"] == 1
    assert first.answer == "answer text"
    assert first.citations[0].url == "https://s.org"
    assert second.citations[0].url == "https://s.org"


def test_domain_filters_mutually_exclusive() -> None:
    with pytest.raises(ValueError):
        youcom.search("x", include_domains=["a.org"], exclude_domains=["b.org"])
