"""you.com Search + Research client with Key Value response caching.

TWO endpoints, TWO jobs (spec §1): Search proposes candidates, Research
verifies. Every response is cached in Key Value keyed by a hash of the request
params, 6h TTL (spec §2).

Contract confirmed against the live docs (2026-07):
  Search   GET  https://ydc-index.io/v1/search   — query params, domains comma-joined
           https://you.com/docs/api-reference/search/v1-search
           response: {"results": {"web": [...], "news": [...]}, "metadata": {...}}
  Research POST https://api.you.com/v1/research   — JSON body
           https://you.com/docs/api-reference/research/v1-research
           body: {"input", "research_effort", "source_control": {...domains[]}}
           response: {"output": {"content", "content_type", "sources": [...]}}

Both authenticate with the `X-API-Key` header. Keys are read from os.environ by
name and never logged, printed, or echoed.
"""

from __future__ import annotations

import json
import os
from enum import StrEnum
from typing import cast

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app import kv
from app.config import settings

AUTH_HEADER = "X-API-Key"
SEARCH_PATH = "/v1/search"
RESEARCH_PATH = "/v1/research"
_SEARCH_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
# Research at deep effort synthesizes across sources and can take minutes.
_RESEARCH_TIMEOUT = httpx.Timeout(300.0, connect=10.0)


class Freshness(StrEnum):
    day = "day"
    week = "week"
    month = "month"
    year = "year"


class Effort(StrEnum):
    lite = "lite"
    standard = "standard"
    deep = "deep"
    exhaustive = "exhaustive"
    frontier = "frontier"


# --- normalized internal shapes (decouple us from you.com's raw JSON) --------

class SearchHit(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""


class SearchResult(BaseModel):
    hits: list[SearchHit] = Field(default_factory=list)


class Citation(BaseModel):
    url: str = ""
    title: str = ""


class ResearchResult(BaseModel):
    answer: str = ""
    citations: list[Citation] = Field(default_factory=list)


def _key_value(env_name: str) -> str:
    val = os.environ.get(env_name, "")
    if not val:
        raise RuntimeError(f"{env_name} is not set — cannot call you.com. See .env.example.")
    return val


def _check_domains(include_domains: list[str] | None, exclude_domains: list[str] | None) -> None:
    # Mutually exclusive, 500-entry cap (spec §2).
    if include_domains and exclude_domains:
        raise ValueError("include_domains and exclude_domains are mutually exclusive")
    for name, value in (("include_domains", include_domains), ("exclude_domains", exclude_domains)):
        if value and len(value) > 500:
            raise ValueError(f"{name} exceeds the 500-entry cap")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _get(base_url: str, path: str, api_key: str, params: dict[str, str | int]) -> dict[str, object]:
    with httpx.Client(base_url=base_url, timeout=_SEARCH_TIMEOUT) as client:
        resp = client.get(path, headers={AUTH_HEADER: api_key}, params=params)
        resp.raise_for_status()
        return cast("dict[str, object]", resp.json())


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _post(base_url: str, path: str, api_key: str, payload: dict[str, object]) -> dict[str, object]:
    with httpx.Client(base_url=base_url, timeout=_RESEARCH_TIMEOUT) as client:
        resp = client.post(path, headers={AUTH_HEADER: api_key}, json=payload)
        resp.raise_for_status()
        return cast("dict[str, object]", resp.json())


def _parse_search(raw: dict[str, object]) -> SearchResult:
    results = raw.get("results")
    web = results.get("web", []) if isinstance(results, dict) else []
    hits: list[SearchHit] = []
    if isinstance(web, list):
        for h in web:
            if not isinstance(h, dict):
                continue
            snippet = h.get("description") or ""
            snippets = h.get("snippets")
            if not snippet and isinstance(snippets, list):
                snippet = " ".join(str(s) for s in snippets)
            hits.append(
                SearchHit(title=str(h.get("title", "")), url=str(h.get("url", "")), snippet=str(snippet))
            )
    return SearchResult(hits=hits)


def _parse_research(raw: dict[str, object]) -> ResearchResult:
    output = raw.get("output")
    if not isinstance(output, dict):
        return ResearchResult()
    content = output.get("content", "")
    answer = content if isinstance(content, str) else json.dumps(content)
    sources = output.get("sources", [])
    citations: list[Citation] = []
    if isinstance(sources, list):
        for s in sources:
            if isinstance(s, dict):
                citations.append(Citation(url=str(s.get("url", "")), title=str(s.get("title", ""))))
    return ResearchResult(answer=str(answer), citations=citations)


def search(
    query: str,
    *,
    freshness: Freshness | str = Freshness.week,
    count: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> SearchResult:
    _check_domains(include_domains, exclude_domains)
    fresh = freshness.value if isinstance(freshness, Freshness) else freshness
    params: dict[str, str | int] = {"query": query, "freshness": fresh, "count": count}
    if include_domains:
        params["include_domains"] = ",".join(include_domains)  # comma-joined for GET
    if exclude_domains:
        params["exclude_domains"] = ",".join(exclude_domains)

    key = kv.cache_key("search", params)
    cached = kv.cache_get(key)
    if cached is not None:
        return SearchResult.model_validate(cached["parsed"])

    raw = _get(settings.you_search_base_url, SEARCH_PATH, _key_value(settings.you_search_key_env), params)
    parsed = _parse_search(raw)
    kv.cache_set(key, {"raw": raw, "parsed": parsed.model_dump()})
    return parsed


def research(
    prompt: str,
    *,
    effort: Effort | str = Effort.deep,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> ResearchResult:
    _check_domains(include_domains, exclude_domains)
    lvl = effort.value if isinstance(effort, Effort) else effort
    payload: dict[str, object] = {"input": prompt, "research_effort": lvl}
    source_control: dict[str, object] = {}
    if include_domains:
        source_control["include_domains"] = include_domains  # arrays in JSON body
    if exclude_domains:
        source_control["exclude_domains"] = exclude_domains
    if source_control:
        payload["source_control"] = source_control

    key = kv.cache_key("research", payload)
    cached = kv.cache_get(key)
    if cached is not None:
        return ResearchResult.model_validate(cached["parsed"])

    raw = _post(settings.you_research_base_url, RESEARCH_PATH, _key_value(settings.you_research_key_env), payload)
    parsed = _parse_research(raw)
    kv.cache_set(key, {"raw": raw, "parsed": parsed.model_dump()})
    return parsed
