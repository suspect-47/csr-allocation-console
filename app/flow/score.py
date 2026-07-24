"""Score stage (spec §3.3).

Extract a cost-per-beneficiary unit ONLY where a source states one. Never
estimate, never divide budget by beneficiary count. Where no source states a
unit, is_stated=false and the number stays null — the card renders
"Cost per beneficiary not published." A fabricated impact figure is the single
worst failure this product can have.
"""

from __future__ import annotations

import re

from app.clients import youcom
from app.clients.youcom import Effort
from app.flow.schemas import CauseStatus, ImpactList, ImpactUnit
from app.flow.state import FlowState

# "$40 per family", "£120 per student per term", "$5 / meal"
_UNIT_COST = re.compile(
    r"([$£€])\s?(\d[\d,]*(?:\.\d+)?)\s*(?:per|/)\s*([a-z][\w\s-]{2,40}?)(?=[.,;:)]|\band\b|$)",
    re.I,
)
_CURRENCY = {"$": "USD", "£": "GBP", "€": "EUR"}


def _extract(answer: str) -> tuple[float, str, str] | None:
    m = _UNIT_COST.search(answer)
    if not m:
        return None
    symbol, amount, label = m.group(1), m.group(2), m.group(3)
    try:
        cost = float(amount.replace(",", ""))
    except ValueError:
        return None
    return cost, _CURRENCY.get(symbol, "USD"), f"per {label.strip()}"


def score_cause(state: FlowState, cause_key: str, org_name: str) -> ImpactUnit:
    state.tool_calls += 1
    r = youcom.research(
        f"Has any source published a specific cost per beneficiary for '{org_name}' "
        f"— for example a cost per family, per student, per meal, or per kit? "
        f"Quote the exact figure and unit if stated.",
        effort=Effort.standard,
    )
    parsed = _extract(r.answer)
    if parsed is None or not r.citations:
        # No source stated a unit cost. Leave it null and unstated.
        return ImpactUnit(is_stated=False)
    cost, currency, label = parsed
    return ImpactUnit(
        unit_label=label,
        unit_cost=cost,
        currency=currency,
        is_stated=True,
        stated_by_url=r.citations[0].url,
    )


def run_score(state: FlowState) -> ImpactList:
    impacts: dict[str, ImpactUnit] = {}
    for v in state.verdicts:
        if v.status != CauseStatus.cleared:
            continue
        key = v.candidate.source_url
        impacts[key] = score_cause(state, key, v.candidate.org_name)
    return ImpactList(impacts=impacts)
