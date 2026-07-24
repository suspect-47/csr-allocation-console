"""Verify stage — the core of the product (spec §3.2).

Six checks per candidate. Each check runs one you.com Research call (deep
effort) for synthesis, then a deterministic classifier turns the research
answer + citations into pass | fail | unknown plus a source URL. The verdict
rule itself is code (decide_verdict), never left to the model.

A check with no source URL is unknown, never pass. Every check result is
recorded whether it passed or not — the blocked ones are product, not waste.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from app.clients import youcom
from app.clients.youcom import Citation, Effort, ResearchResult
from app.flow.schemas import (
    Candidate,
    CheckName,
    CheckOutcome,
    CheckResult,
    NeedType,
    Verdict,
    VerdictList,
    decide_verdict,
)
from app.flow.scout import FUNDRAISING_PLATFORMS, registrable_domain
from app.flow.state import FlowState

REGISTRY_DOMAINS = frozenset(
    {
        "guidestar.org",
        "charitynavigator.org",
        "irs.gov",
        "gov.uk",
        "sec.gov",
        "ngodarpan.gov.in",
        "charitycommission.gov.uk",
        "candid.org",
        "propublica.org",  # Nonprofit Explorer
    }
)

ADVERSE_KEYWORDS = (
    "fraud",
    "scam",
    "embezzle",
    "misappropriat",
    "lawsuit",
    "indict",
    "convicted",
    "revoked",
    "deregistered",
    "regulatory complaint",
    "ftc complaint",
    "deceptive",
    "ponzi",
    "money laundering",
)

_NEGATION = ("does not exist", "no evidence", "could not find", "no such organization", "unable to find")

# EIN, UK charity number, India 12A/80G, generic "registered charity No. …"
_REG_PATTERNS = (
    re.compile(r"\b\d{2}-\d{7}\b"),                    # US EIN
    re.compile(r"charity\s+(?:reg(?:istration)?\.?\s*)?(?:no\.?|number)\s*[:#]?\s*\d{5,8}", re.I),
    re.compile(r"\b12A\b|\b80G\b", re.I),
    re.compile(r"registered\s+charity", re.I),
    re.compile(r"\bEIN\b", re.I),
)

_PAYMENT_HANDLE = re.compile(r"(venmo\.com/|paypal\.me/|cash\.app/\$|cashapp|@\w+\s*(?:on\s+)?venmo)", re.I)
_DONATE_PATH = re.compile(r"/(donate|give|support|contribute|appeal)", re.I)

_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONTH_YEAR = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{4})\b", re.I
)
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _excerpt(text: str) -> str:
    return text.strip().replace("\n", " ")[:200]


def _distinct_domains(citations: list[Citation]) -> list[str]:
    out: list[str] = []
    for c in citations:
        d = registrable_domain(c.url)
        if d and d not in out:
            out.append(d)
    return out


def _first_citation_on(citations: list[Citation], domains: frozenset[str] | set[str]) -> Citation | None:
    for c in citations:
        d = registrable_domain(c.url)
        if d and d in domains:
            return c
    return None


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_dates(text: str) -> list[datetime]:
    found: list[datetime] = []
    for y, mo, d in _ISO_DATE.findall(text):
        try:
            found.append(datetime(int(y), int(mo), int(d), tzinfo=UTC))
        except ValueError:
            continue
    for mon, y in _MONTH_YEAR.findall(text):
        found.append(datetime(int(y), _MONTHS[mon.lower()[:3]], 1, tzinfo=UTC))
    return found


# --- individual checks ------------------------------------------------------

def _check_exists(cand: Candidate, r: ResearchResult) -> CheckResult:
    answer = r.answer.lower()
    src = None
    if cand.org_domain:
        src = _first_citation_on(r.citations, {cand.org_domain})
    if src is None:
        src = _first_citation_on(r.citations, REGISTRY_DOMAINS)
    if any(neg in answer for neg in _NEGATION):
        return CheckResult(check_name=CheckName.organization_exists, result=CheckOutcome.failed,
                           excerpt=_excerpt(r.answer))
    if src is not None:
        return CheckResult(check_name=CheckName.organization_exists, result=CheckOutcome.passed,
                           source_url=src.url, source_title=src.title, excerpt=_excerpt(r.answer))
    return CheckResult(check_name=CheckName.organization_exists, result=CheckOutcome.unknown,
                       excerpt=_excerpt(r.answer))


def _check_registration(cand: Candidate, r: ResearchResult) -> CheckResult:
    has_id = any(p.search(r.answer) for p in _REG_PATTERNS)
    src = _first_citation_on(r.citations, REGISTRY_DOMAINS) or (r.citations[0] if r.citations else None)
    if has_id and src is not None:
        return CheckResult(check_name=CheckName.registration_status, result=CheckOutcome.passed,
                           source_url=src.url, source_title=src.title, excerpt=_excerpt(r.answer))
    # Absence of a registration id is not disproof — unknown, not fail.
    return CheckResult(check_name=CheckName.registration_status, result=CheckOutcome.unknown,
                       excerpt=_excerpt(r.answer))


def _check_corroboration(cand: Candidate, r: ResearchResult) -> CheckResult:
    domains = _distinct_domains(r.citations)
    own = cand.org_domain
    independent = [
        d for d in domains if d != own and d not in FUNDRAISING_PLATFORMS
    ]
    if len(domains) >= 2 and independent:
        src = _first_citation_on(r.citations, set(independent))
        return CheckResult(check_name=CheckName.independent_corroboration, result=CheckOutcome.passed,
                           source_url=src.url if src else None,
                           source_title=src.title if src else None, excerpt=_excerpt(r.answer))
    if r.citations:
        return CheckResult(check_name=CheckName.independent_corroboration, result=CheckOutcome.failed,
                           excerpt=_excerpt(r.answer))
    return CheckResult(check_name=CheckName.independent_corroboration, result=CheckOutcome.unknown,
                       excerpt=_excerpt(r.answer))


def _check_recency(cand: Candidate, r: ResearchResult) -> CheckResult:
    window = 30 if cand.need_type == NeedType.acute else 180
    cutoff = _now() - timedelta(days=window)
    dates = _parse_dates(r.answer)
    src = r.citations[0] if r.citations else None
    if not dates:
        return CheckResult(check_name=CheckName.recency, result=CheckOutcome.unknown,
                           source_url=src.url if src else None,
                           source_title=src.title if src else None, excerpt=_excerpt(r.answer))
    most_recent = max(dates)
    if most_recent >= cutoff and src is not None:
        return CheckResult(check_name=CheckName.recency, result=CheckOutcome.passed,
                           source_url=src.url, source_title=src.title, excerpt=_excerpt(r.answer))
    return CheckResult(check_name=CheckName.recency, result=CheckOutcome.failed,
                       excerpt=_excerpt(r.answer))


def _check_solicitation(cand: Candidate, r: ResearchResult) -> CheckResult:
    # Donation on org's own domain or a named platform — not a bare handle.
    own = {cand.org_domain} if cand.org_domain else set()
    own_donate = None
    for c in r.citations:
        d = registrable_domain(c.url)
        if d in own and _DONATE_PATH.search(urlparse(c.url).path):
            own_donate = c
            break
    platform = _first_citation_on(r.citations, FUNDRAISING_PLATFORMS)
    if own_donate or platform:
        src = own_donate or platform
        assert src is not None
        return CheckResult(check_name=CheckName.solicitation_channel, result=CheckOutcome.passed,
                           source_url=src.url, source_title=src.title, excerpt=_excerpt(r.answer))
    if _PAYMENT_HANDLE.search(r.answer):
        return CheckResult(check_name=CheckName.solicitation_channel, result=CheckOutcome.failed,
                           excerpt=_excerpt(r.answer))
    return CheckResult(check_name=CheckName.solicitation_channel, result=CheckOutcome.unknown,
                       excerpt=_excerpt(r.answer))


def _check_contradiction(cand: Candidate, r: ResearchResult) -> CheckResult:
    # An org vouching for itself is not evidence — this research call excludes
    # the org's own domain (see run_verify). Any adverse signal blocks.
    answer = r.answer.lower()
    if any(k in answer for k in ADVERSE_KEYWORDS):
        src = r.citations[0] if r.citations else None
        return CheckResult(check_name=CheckName.contradiction_scan, result=CheckOutcome.failed,
                           source_url=src.url if src else None,
                           source_title=src.title if src else None, excerpt=_excerpt(r.answer))
    if r.citations:
        # We searched and found nothing adverse; cite what we looked at.
        src = r.citations[0]
        return CheckResult(check_name=CheckName.contradiction_scan, result=CheckOutcome.passed,
                           source_url=src.url, source_title=src.title, excerpt=_excerpt(r.answer))
    return CheckResult(check_name=CheckName.contradiction_scan, result=CheckOutcome.unknown,
                       excerpt=_excerpt(r.answer))


Classifier = Callable[[Candidate, ResearchResult], CheckResult]


def check_specs(cand: Candidate) -> list[tuple[Classifier, str, list[str] | None]]:
    """The six checks as (classifier, research prompt, exclude_domains), in
    order. Single source of truth for the prompts — verify_candidate and the
    fixture recorder both iterate this so captures match live calls exactly.
    """
    name, dom = cand.org_name, cand.org_domain or "unknown domain"
    own = [cand.org_domain] if cand.org_domain else None
    return [
        (_check_exists, f"Does the nonprofit '{name}' ({dom}) exist? Find its primary domain, legal or about page, or an official nonprofit registry listing.", None),
        (_check_registration, f"What nonprofit registration identifier does '{name}' ({dom}) hold — EIN, UK charity number, India 12A/80G, or equivalent? Cite the registry.", None),
        (_check_corroboration, f"Which independent sources report this need: {cand.claim}. List distinct outlets covering '{name}' in {cand.geography}.", None),
        (_check_recency, f"What is the date of the most recent primary report of this need for '{name}' in {cand.geography}: {cand.claim}. Give the publication date.", None),
        (_check_solicitation, f"How does '{name}' ({dom}) accept donations — a donation page on its own domain, a named fundraising platform, or a payment handle? Give the destination URL.", None),
        (_check_contradiction, f"Search for fraud, scam, lawsuit, regulatory complaint, or deregistration signals about the nonprofit '{name}'.", own),
    ]


def verify_candidate(state: FlowState, cand: Candidate) -> Verdict:
    checks: list[CheckResult] = []
    for classifier, prompt, exclude in check_specs(cand):
        state.tool_calls += 1
        r = youcom.research(prompt, effort=Effort.deep, exclude_domains=exclude)
        checks.append(classifier(cand, r))
    status, blocking = decide_verdict(checks)
    return Verdict(candidate=cand, checks=checks, status=status, blocking_check=blocking)


def run_verify(state: FlowState) -> VerdictList:
    return VerdictList(verdicts=[verify_candidate(state, c) for c in state.candidates])
