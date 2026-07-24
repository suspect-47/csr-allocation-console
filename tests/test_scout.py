"""Scout dedupe + deterministic extraction (spec §3.1)."""

from __future__ import annotations

from app.flow.schemas import Candidate, NeedType
from app.flow.scout import (
    _dedupe,
    is_org_domain,
    org_name_from_domain,
    registrable_domain,
)


def test_registrable_domain_strips_www() -> None:
    assert registrable_domain("https://www.helporg.org/donate") == "helporg.org"
    assert registrable_domain("not-a-url") is None


def test_org_name_from_domain() -> None:
    # Identity comes from the domain, not a deep page's title.
    assert org_name_from_domain("watermission.org") == "Watermission"
    assert org_name_from_domain("water-is-life.org") == "Water Is Life"


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


def test_is_org_domain_filters_non_orgs() -> None:
    assert is_org_domain("waterislifekenya.org") is True
    assert is_org_domain(None) is False
    for d in ("guidestar.org", "youtube.com", "nytimes.com", "gofundme.com", "wikipedia.org"):
        assert is_org_domain(d) is False
    assert is_org_domain("amp.cnn.com") is False  # subdomain of a non-org domain


def test_government_domains_excluded() -> None:
    for d in ("makueni.go.ke", "irs.gov", "charitycommission.gov.uk", "army.mil"):
        assert is_org_domain(d) is False
