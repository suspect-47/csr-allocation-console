"""Compose LLM polish path + deterministic fallback (spec §3.4).

The LLM may only rewrite headline/summary; bullets stay cited and the record
never depends on the LLM. Both branches are covered here without a live call.
"""

from __future__ import annotations

import pytest
from app.flow import compose
from app.flow.schemas import (
    Candidate,
    CauseStatus,
    CheckName,
    CheckOutcome,
    CheckResult,
    NeedType,
    Verdict,
)


def _cleared_verdict() -> Verdict:
    cand = Candidate(org_name="Help Org", org_domain="help.org", claim="urgent need",
                     source_url="https://help.org", source_title="Help Org",
                     need_type=NeedType.acute, pillar="Health", geography="Region")
    checks = [CheckResult(check_name=n, result=CheckOutcome.passed,
                          source_url=f"https://help.org/{n.value}", source_title="e", excerpt="x")
              for n in CheckName]
    return Verdict(candidate=cand, checks=checks, status=CauseStatus.cleared, blocking_check=None)


def test_compose_uses_llm_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        compose.llm, "polish_copy",
        lambda *a, **k: {"headline": "Polished head", "summary": "Polished summary."},
    )
    card = compose.compose_card(_cleared_verdict())
    assert card.headline == "Polished head"
    assert card.summary == "Polished summary."
    assert len(card.bullets) == 3               # bullets stay cited regardless
    assert all(b.source_url for b in card.bullets)


def test_compose_falls_back_when_llm_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(compose.llm, "polish_copy", lambda *a, **k: None)
    card = compose.compose_card(_cleared_verdict())
    assert "Help Org" in card.headline           # deterministic copy
    assert len(card.bullets) == 3


def test_compose_llm_cannot_break_length(monkeypatch: pytest.MonkeyPatch) -> None:
    # Even an overlong LLM response is truncated to the card contract.
    monkeypatch.setattr(
        compose.llm, "polish_copy",
        lambda *a, **k: {"headline": "x" * 200, "summary": "y" * 500},
    )
    card = compose.compose_card(_cleared_verdict())
    assert len(card.headline) <= 60
    assert len(card.summary) <= 240
