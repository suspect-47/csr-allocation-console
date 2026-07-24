"""Verify-stage classifier logic (spec §3.2, §9 step 4).

These test the deterministic classifiers against synthetic ResearchResults —
they exercise code, not recorded captures, so they run offline without keys.
The end-to-end replay against real captures is the eval gate (test_eval_gate).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.clients.youcom import Citation, ResearchResult
from app.flow import verify
from app.flow.schemas import CheckOutcome, NeedType


def _cand(domain: str | None = "helporg.org", need: NeedType = NeedType.acute) -> object:
    from app.flow.schemas import Candidate

    return Candidate(org_name="Help Org", org_domain=domain, claim="urgent need",
                     source_url="https://helporg.org", source_title="Help Org",
                     need_type=need, pillar="Health", geography="Region")


def test_exists_pass_on_own_domain() -> None:
    r = ResearchResult(answer="Help Org is a registered nonprofit.",
                       citations=[Citation(url="https://helporg.org/about", title="About")])
    result = verify._check_exists(_cand(), r)
    assert result.result == CheckOutcome.passed
    assert result.source_url == "https://helporg.org/about"


def test_exists_fail_on_negation() -> None:
    r = ResearchResult(answer="We could not find any evidence this organization exists.", citations=[])
    assert verify._check_exists(_cand(), r).result == CheckOutcome.failed


def test_exists_unknown_without_source() -> None:
    r = ResearchResult(answer="Possibly a nonprofit.", citations=[])
    assert verify._check_exists(_cand(), r).result == CheckOutcome.unknown


def test_corroboration_needs_independent_domain() -> None:
    two_independent = ResearchResult(answer="Reported widely.", citations=[
        Citation(url="https://reuters.com/x"), Citation(url="https://bbc.com/y")])
    assert verify._check_corroboration(_cand(), two_independent).result == CheckOutcome.passed

    only_own = ResearchResult(answer="Only the org reports it.",
                              citations=[Citation(url="https://helporg.org/news")])
    assert verify._check_corroboration(_cand(), only_own).result == CheckOutcome.failed

    none = ResearchResult(answer="No sources.", citations=[])
    assert verify._check_corroboration(_cand(), none).result == CheckOutcome.unknown


def test_corroboration_excludes_fundraising_platforms() -> None:
    r = ResearchResult(answer="Fundraiser only.", citations=[
        Citation(url="https://gofundme.com/abc"), Citation(url="https://helporg.org/x")])
    # gofundme is a platform, helporg is the org's own — no independent domain.
    assert verify._check_corroboration(_cand(), r).result == CheckOutcome.failed


def test_contradiction_fails_on_adverse_signal() -> None:
    r = ResearchResult(answer="A regulatory complaint alleges fraud by the group.",
                       citations=[Citation(url="https://ag.gov/case")])
    assert verify._check_contradiction(_cand(), r).result == CheckOutcome.failed


def test_contradiction_passes_when_clean_with_source() -> None:
    r = ResearchResult(answer="No adverse findings; the group is well regarded.",
                       citations=[Citation(url="https://news.org/profile")])
    assert verify._check_contradiction(_cand(), r).result == CheckOutcome.passed


def test_recency_within_window_passes() -> None:
    recent = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
    r = ResearchResult(answer=f"The appeal was published {recent}.",
                       citations=[Citation(url="https://news.org/a")])
    assert verify._check_recency(_cand(need=NeedType.acute), r).result == CheckOutcome.passed


def test_recency_stale_fails() -> None:
    r = ResearchResult(answer="The report is dated 2019-01-01.",
                       citations=[Citation(url="https://news.org/a")])
    assert verify._check_recency(_cand(need=NeedType.acute), r).result == CheckOutcome.failed


def test_solicitation_own_donate_page_passes() -> None:
    r = ResearchResult(answer="Donate here.", citations=[Citation(url="https://helporg.org/donate")])
    assert verify._check_solicitation(_cand(), r).result == CheckOutcome.passed


def test_solicitation_bare_handle_fails() -> None:
    r = ResearchResult(answer="Send money to venmo.com/@random-person.", citations=[])
    assert verify._check_solicitation(_cand(), r).result == CheckOutcome.failed


def test_registration_pass_with_ein() -> None:
    r = ResearchResult(answer="EIN 12-3456789 on file.",
                       citations=[Citation(url="https://guidestar.org/x")])
    assert verify._check_registration(_cand(), r).result == CheckOutcome.passed


def test_registration_unknown_without_id() -> None:
    r = ResearchResult(answer="No registration details found.", citations=[])
    assert verify._check_registration(_cand(), r).result == CheckOutcome.unknown
