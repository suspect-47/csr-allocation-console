"""Render Key Value (Redis/Valkey protocol): job queue + you.com response cache.

Two responsibilities, deliberately in one module because they share the client:
  - Queue: a Redis list used as a FIFO work queue. Web/cron LPUSH, worker BRPOP.
  - Cache: you.com responses keyed by a hash of request params, 6h TTL (spec §2).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import redis

from app.config import settings

_client: redis.Redis | None = None

QUEUE_KEY = "csr:jobs"
_CACHE_PREFIX = "csr:youcache:"


def client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.kv_url, decode_responses=True)
    return _client


# --- queue ------------------------------------------------------------------

def enqueue_job(job: dict[str, Any]) -> None:
    client().lpush(QUEUE_KEY, json.dumps(job))


def dequeue_job(timeout_seconds: int = 5) -> dict[str, Any] | None:
    result = client().brpop([QUEUE_KEY], timeout=timeout_seconds)
    if result is None:
        return None
    _, payload = result
    job: dict[str, Any] = json.loads(payload)
    return job


def queue_depth() -> int:
    return int(client().llen(QUEUE_KEY))


# --- you.com response cache -------------------------------------------------

def cache_key(namespace: str, params: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(params, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"{_CACHE_PREFIX}{namespace}:{digest}"


def cache_get(key: str) -> dict[str, Any] | None:
    raw = client().get(key)
    if not raw:
        return None
    decoded: dict[str, Any] = json.loads(raw)
    return decoded


def cache_set(key: str, value: dict[str, Any]) -> None:
    client().set(key, json.dumps(value), ex=settings.youcom_cache_ttl_seconds)


def healthcheck() -> bool:
    return bool(client().ping())
