"""Scout dedupe + deterministic extraction (spec §3.1)."""

from __future__ import annotations

from app.flow.schemas import Candidate, NeedType
from app.flow.scout import _clean_org_name, _dedupe, registrable_domain


def test_registrable_domain_strips_www() -> None:
    assert registrable_domain("https://www.helporg.org/donate") == "helporg.org"
    assert registrable_domain("not-a-url") is None


def test_clean_org_name_takes_first_segment() -> None:
    assert _clean_org_name("Help Org | Donate") == "Help Org"
    assert _clean_org_name("Help Org - Home") == "Help Org"
    assert _clean_org_name("Help Org") == "Help Org"


def _cand(name: str, domain: str | None) -> Candidate:
    return Candidate(org_name=name, org_domain=domain, claim="c",
                     source_url=f"https://{domain or 'x'}.test", source_title=name,
                     need_type=NeedType.acute, pillar="P", geography="G")


def test_dedupe_on_domain() -> None:
    out = _dedupe([_cand("A", "a.org"), _cand("A dup", "a.org"), _cand("B", "b.org")])
    assert {c.org_domain for c in out} == {"a.org", "b.org"}


def test_dedupe_fuzzy_name_when_no_domain() -> None:
    out = _dedupe([_cand("Rapid Relief Fund", None), _cand("Rapid Relief Fund!", None)])
    assert len(out) == 1
