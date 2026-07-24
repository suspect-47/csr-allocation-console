"""you.com Search + Research client with Key Value response caching.

TWO endpoints, TWO jobs (spec §1): Search proposes candidates, Research
verifies. Every response is cached in Key Value keyed by a hash of the request
params, 6h TTL (spec §2) — the pipeline runs hundreds of times in dev and the
free credits will not survive uncached calls.

╔═ VERIFY against live docs before the first live call (spec §2) ═════════════╗
║ Base URLs, the auth header name, and the exact response JSON keys are NOT   ║
║ reproduced from the spec on purpose. This module was written without doc    ║
║ access (fetch was unavailable at build time). Confirm and adjust:           ║
║   - SEARCH_PATH / RESEARCH_PATH and the base URLs in .env                   ║
║   - AUTH_HEADER name                                                        ║
║   - the field names read in _parse_search / _parse_research                 ║
║ docs: https://docs.you.com/api-reference/search/v1-search                   ║
║       https://you.com/docs/api-reference/research/v1-research               ║
╚════════════════════════════════════════════════════════════════════════════╝

The key is read from os.environ by name and never logged, printed, or echoed.
"""

from __future__ import annotations

import os
from enum import StrEnum
from typing import cast

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app import kv
from app.config import settings

AUTH_HEADER = "X-API-Key"          # VERIFY
SEARCH_PATH = "/search"            # VERIFY
RESEARCH_PATH = "/research"        # VERIFY
_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


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


def _domain_filters(
    params: dict[str, object],
    include_domains: list[str] | None,
    exclude_domains: list[str] | None,
) -> None:
    # Mutually exclusive, 500-entry cap (spec §2).
    if include_domains and exclude_domains:
        raise ValueError("include_domains and exclude_domains are mutually exclusive")
    for name, value in (("include_domains", include_domains), ("exclude_domains", exclude_domains)):
        if value:
            if len(value) > 500:
                raise ValueError(f"{name} exceeds the 500-entry cap")
            params[name] = value


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _post(base_url: str, path: str, api_key: str, payload: dict[str, object]) -> dict[str, object]:
    with httpx.Client(base_url=base_url, timeout=_TIMEOUT) as client:
        resp = client.post(path, headers={AUTH_HEADER: api_key}, json=payload)
        resp.raise_for_status()
        return cast("dict[str, object]", resp.json())


def _parse_search(raw: dict[str, object]) -> SearchResult:
    # VERIFY: adjust to the live response shape. Tolerant of the common keys.
    hits_raw = raw.get("hits") or raw.get("results") or raw.get("web") or []
    hits: list[SearchHit] = []
    if isinstance(hits_raw, list):
        for h in hits_raw:
            if not isinstance(h, dict):
                continue
            snippet = h.get("snippet") or h.get("description") or ""
            if not snippet and isinstance(h.get("snippets"), list):
                snippet = " ".join(str(s) for s in h["snippets"])
            hits.append(
                SearchHit(
                    title=str(h.get("title", "")),
                    url=str(h.get("url", "")),
                    snippet=str(snippet),
                )
            )
    return SearchResult(hits=hits)


def _parse_research(raw: dict[str, object]) -> ResearchResult:
    # VERIFY: adjust to the live response shape.
    answer = raw.get("answer") or raw.get("output") or raw.get("summary") or ""
    cites_raw = raw.get("citations") or raw.get("sources") or raw.get("search_results") or []
    citations: list[Citation] = []
    if isinstance(cites_raw, list):
        for c in cites_raw:
            if isinstance(c, dict):
                citations.append(
                    Citation(url=str(c.get("url", "")), title=str(c.get("title", "")))
                )
            elif isinstance(c, str):
                citations.append(Citation(url=c))
    return ResearchResult(answer=str(answer), citations=citations)


def search(
    query: str,
    *,
    freshness: Freshness | str = Freshness.week,
    count: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> SearchResult:
    fresh = freshness.value if isinstance(freshness, Freshness) else freshness
    payload: dict[str, object] = {"query": query, "freshness": fresh, "count": count}
    _domain_filters(payload, include_domains, exclude_domains)

    key = kv.cache_key("search", payload)
    cached = kv.cache_get(key)
    if cached is not None:
        return SearchResult.model_validate(cached["parsed"])

    raw = _post(settings.you_search_base_url, SEARCH_PATH, _key_value(settings.you_search_key_env), payload)
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
    lvl = effort.value if isinstance(effort, Effort) else effort
    payload: dict[str, object] = {"query": prompt, "effort": lvl}
    _domain_filters(payload, include_domains, exclude_domains)

    key = kv.cache_key("research", payload)
    cached = kv.cache_get(key)
    if cached is not None:
        return ResearchResult.model_validate(cached["parsed"])

    raw = _post(settings.you_research_base_url, RESEARCH_PATH, _key_value(settings.you_research_key_env), payload)
    parsed = _parse_research(raw)
    kv.cache_set(key, {"raw": raw, "parsed": parsed.model_dump()})
    return parsed
