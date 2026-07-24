"""Scout stage (spec §3.1).

One query per (pillar × geography) pair. Acute framing at freshness=week,
development framing at freshness=month. Scout proposes; it does not judge —
everything it emits is unverified by definition. Candidate extraction is
deterministic (host → domain, title → name, snippet → claim) so this stage
adds no model guesswork before verification.
"""

from __future__ import annotations

from urllib.parse import urlparse

from rapidfuzz import fuzz

from app.clients import youcom
from app.clients.youcom import Freshness
from app.flow.schemas import Candidate, CandidateList, NeedType
from app.flow.state import FlowState

# Donation destinations that are not the org's own domain (spec §3.2 check 5,
# §3.1 corroboration). A bare fundraising platform is not the org itself.
FUNDRAISING_PLATFORMS = frozenset(
    {
        "gofundme.com",
        "justgiving.com",
        "donorbox.org",
        "gogetfunding.com",
        "fundly.com",
        "mightycause.com",
        "classy.org",
        "givebutter.com",
        "ketto.org",
        "milaap.org",
    }
)

# Domains that are never the org itself: news, social, reference, directories,
# blogging/marketplaces. A hit on these is coverage or a listing — evidence that
# verify's Research surfaces, not a candidate to propose. Filtering them keeps
# Scout emitting real org sites instead of article titles.
NON_ORG_DOMAINS = frozenset(
    {
        # news
        "nytimes.com", "washingtonpost.com", "cnn.com", "bbc.com", "bbc.co.uk",
        "reuters.com", "apnews.com", "theguardian.com", "npr.org", "forbes.com",
        "aljazeera.com", "bloomberg.com", "wsj.com", "usatoday.com", "time.com",
        "vox.com", "axios.com", "politico.com", "huffpost.com", "cnbc.com",
        "nbcnews.com", "cbsnews.com", "abcnews.go.com", "dailymail.co.uk",
        "nation.africa", "standardmedia.co.ke", "the-star.co.ke", "citizen.digital",
        # social / video / forums / blogging
        "facebook.com", "twitter.com", "x.com", "instagram.com", "linkedin.com",
        "youtube.com", "tiktok.com", "reddit.com", "pinterest.com", "threads.net",
        "medium.com", "substack.com", "quora.com", "blogspot.com", "wordpress.com",
        "wixsite.com",
        # reference / directories / registries (evidence, not orgs)
        "wikipedia.org", "wikimedia.org", "guidestar.org", "charitynavigator.org",
        "candid.org", "propublica.org", "greatnonprofits.org", "causeiq.com",
        "rocketreach.co", "zoominfo.com", "crunchbase.com", "glassdoor.com",
        "indeed.com", "idealist.org",
        # generic / marketplaces
        "amazon.com", "google.com", "yahoo.com", "bing.com",
    }
)

_NAME_MATCH_THRESHOLD = 90  # rapidfuzz token_sort_ratio


def _matches(domain: str, blocklist: frozenset[str]) -> bool:
    return any(domain == d or domain.endswith("." + d) for d in blocklist)


def is_org_domain(domain: str | None) -> bool:
    """A candidate must have a domain that is plausibly the org's own site."""
    if not domain:
        return False
    return not _matches(domain, FUNDRAISING_PLATFORMS) and not _matches(domain, NON_ORG_DOMAINS)


def registrable_domain(url: str) -> str | None:
    host = urlparse(url).netloc.lower()
    if not host:
        return None
    host = host.removeprefix("www.")
    return host or None


def _clean_org_name(title: str) -> str:
    # Titles are commonly "Org Name | Home" or "Org Name - Donate". Take the
    # first segment; never invent a name the source did not carry.
    for sep in (" | ", " – ", " — ", " - ", ": "):
        if sep in title:
            return title.split(sep, 1)[0].strip()
    return title.strip()


def _pair_query(pillar: str, geography: str, need_type: NeedType) -> str:
    if need_type == NeedType.acute:
        return f"{pillar} urgent unmet need {geography} nonprofit relief appeal"
    return f"{pillar} {geography} nonprofit program long-term funding need"


def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
    kept: list[Candidate] = []
    seen_domains: set[str] = set()
    for cand in candidates:
        if cand.org_domain:
            if cand.org_domain in seen_domains:
                continue
            seen_domains.add(cand.org_domain)
            kept.append(cand)
            continue
        # No domain — fall back to fuzzy org_name against what we've kept.
        dup = any(
            fuzz.token_sort_ratio(cand.org_name, k.org_name) >= _NAME_MATCH_THRESHOLD
            for k in kept
        )
        if not dup:
            kept.append(cand)
    return kept


def run_scout(state: FlowState) -> CandidateList:
    profile = state.profile()
    raw: list[Candidate] = []

    for pillar, geography in profile.query_pairs():
        for need_type, freshness in (
            (NeedType.acute, Freshness.week),
            (NeedType.development, Freshness.month),
        ):
            result = youcom.search(
                _pair_query(pillar, geography, need_type),
                freshness=freshness,
                count=10,
            )
            state.tool_calls += 1
            for hit in result.hits:
                if not hit.url:
                    continue
                domain = registrable_domain(hit.url)
                # Only propose hits that are plausibly the org's own site. News,
                # social, directories, and fundraising platforms are coverage or
                # listings — evidence for verify, not candidates.
                if not is_org_domain(domain):
                    continue
                raw.append(
                    Candidate(
                        org_name=_clean_org_name(hit.title) or domain or "Unknown",
                        org_domain=domain,
                        claim=hit.snippet.strip(),
                        source_url=hit.url,
                        source_title=hit.title,
                        need_type=need_type,
                        pillar=pillar,
                        geography=geography,
                    )
                )

    return CandidateList(candidates=_dedupe(raw))
