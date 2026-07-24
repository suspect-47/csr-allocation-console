"""Reasoning model access via litellm (the layer CrewAI's LLM wraps).

Deviation from spec §1: OpenAI instead of Claude (user directive, 2026-07). The
model polishes card copy ONLY — it never makes a verification or allocation
decision; those stay in code. Gated on OPENAI_API_KEY and best-effort: any
failure returns None so Compose falls back to deterministic copy and a run
never depends on the LLM. The key is read by name via litellm; never logged.
"""

from __future__ import annotations

import json
import logging
import os

from app.config import settings

log = logging.getLogger(__name__)

_SYSTEM = (
    "You rewrite funding-card copy for a corporate giving console. State what is "
    "happening and what money does. No urgency manufacturing, no second-person "
    "imperatives, no imagery of individuals in distress. Use ONLY the facts "
    "provided — invent nothing, add no numbers. Return strict JSON: "
    '{"headline": string <=60 chars, "summary": string <=240 chars}.'
)


def available() -> bool:
    return bool(os.environ.get(settings.openai_key_env))


def polish_copy(
    org_name: str,
    pillar: str,
    geography: str,
    claim: str,
    evidence_lines: list[str],
) -> dict[str, str] | None:
    """Rewrite headline + summary from verified facts. None on unavailable/failure."""
    if not available():
        return None
    try:
        import litellm

        user = (
            f"Organization: {org_name}\nPillar: {pillar}\nGeography: {geography}\n"
            f"Claim: {claim}\nVerified evidence:\n"
            + "\n".join(f"- {e}" for e in evidence_lines)
        )
        resp = litellm.completion(
            model=settings.crew_model,
            messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        data = json.loads(content)
        headline = str(data.get("headline", "")).strip()
        summary = str(data.get("summary", "")).strip()
        if not headline or not summary:
            return None
        return {"headline": headline[:60], "summary": summary[:240]}
    except Exception as exc:  # noqa: BLE001 - LLM polish is best-effort, never fatal
        log.warning("card copy polish failed (%s); using deterministic copy", type(exc).__name__)
        return None
