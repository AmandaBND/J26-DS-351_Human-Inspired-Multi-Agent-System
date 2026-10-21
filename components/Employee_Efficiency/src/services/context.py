"""Contextual analysis: separates what the employee controls from what they do not."""
from __future__ import annotations

import pandas as pd

from src.config import BASELINE_YEAR
from src.schemas.assessment import ContextFindings

POSITIVE = ("confident", "helped", "smoothly", "good", "fine", "achievable", "great")
NEGATIVE = ("too many", "late", "overtime", "struggling", "unfamiliar", "not confident", "down",
            "outages", "slow", "delayed", "backlog", "cheaper", "budget", "hard", "limits", "putting off")
TAGS = {
    "workload": ("too many", "overtime", "backlog", "keep up", "workload", "working late"),
    "training": ("unfamiliar", "training", "not confident", "new equipment", "new systems"),
    "process": ("system was down", "outages", "approval", "delayed"),
    "parts": ("spare part", "waiting for parts", "long waits"),
    "incomplete": ("missing approval", "incomplete", "missing details", "chasing"),
    "price": ("competitor", "cheaper", "budget", "price"),
}


def score_feedback(texts: list[str]) -> tuple[float, dict[str, int]]:
    """Transparent lexicon scoring (no LLM, no raw text leaves the machine)."""
    pos = neg = 0
    tags = {k: 0 for k in TAGS}
    for t in texts:
        low = t.lower()
        pos += sum(w in low for w in POSITIVE)
        neg += sum(w in low for w in NEGATIVE)
        for tag, words in TAGS.items():
            if any(w in low for w in words):
                tags[tag] += 1
    sentiment = (pos - neg) / max(1, pos + neg)
    return round(sentiment, 2), tags


def analyse_context(
    ctx: pd.DataFrame,
    fb: pd.DataFrame,
    emp_id: int,
    peer_share: float,
    recent_periods: list[str] | None = None,
    role_employee_ids: list[int] | None = None,
) -> ContextFindings:
    """Compare recent operating conditions with employee and role-specific history."""
    def mean(frame: pd.DataFrame, column: str, default: float = 0.0) -> float:
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        return float(values.mean()) if not values.empty else default

    c = ctx[ctx["employee_id"] == emp_id].sort_values("period")
    base = c[c["period"].str[:4] == str(BASELINE_YEAR)]
    recent = c[c["period"].isin(recent_periods)] if recent_periods else c.iloc[-3:]
    own_baseline_jobs = mean(base, "jobs_assigned")
    own_recent_jobs = mean(recent, "jobs_assigned")
    role_rows = ctx[ctx["employee_id"].isin(role_employee_ids or [emp_id])]
    role_baseline = role_rows[role_rows["period"].str[:4] == str(BASELINE_YEAR)]
    role_recent = role_rows[role_rows["period"].isin(recent["period"])]
    baseline_month_count = max(1, role_baseline["period"].nunique())
    recent_month_count = max(1, role_recent["period"].nunique())
    role_baseline_monthly = float(role_baseline["jobs_assigned"].sum() / baseline_month_count)
    role_recent_monthly = float(role_recent["jobs_assigned"].sum() / recent_month_count)
    employee_ratio = own_recent_jobs / own_baseline_jobs if own_baseline_jobs > 0 else 1.0
    seasonal_factor = role_recent_monthly / role_baseline_monthly if role_baseline_monthly > 0 else 1.0
    ratio = employee_ratio / seasonal_factor if seasonal_factor > 0 else employee_ratio
    cdelta = mean(recent, "avg_complexity", 3.0) - mean(base, "avg_complexity", 3.0)
    overtime = mean(recent, "overtime_hours")
    ddelta = mean(recent, "system_downtime_hours") - mean(base, "system_downtime_hours")
    price = mean(recent, "price_change_pct")
    offers = mean(recent, "competitor_offers")
    budget = mean(recent, "budget_constrained_share")
    texts = fb[(fb["employee_id"] == emp_id) & (fb["period"].isin(recent["period"]))]["text"].tolist()
    sentiment, tags = score_feedback(texts)
    parts_delta = mean(recent, "parts_wait_share") - mean(base, "parts_wait_share")
    incomplete_delta = mean(recent, "incomplete_input_share") - mean(base, "incomplete_input_share")

    notes = []
    if ratio >= 1.2:
        notes.append(
            f"Jobs assigned are {ratio:.2f} times this employee's own usual level in 2024; "
            f"overtime is about {overtime:.0f} hours a month."
        )
    if cdelta >= 0.5:
        notes.append(
            f"Average job complexity is about {cdelta:.1f} points above this employee's "
            "own usual level in 2024."
        )
    if ddelta >= 5:
        notes.append(
            f"System downtime is about {ddelta:.0f} hours a month above its 2024 level."
        )
    if price >= 4 or offers >= 2.5:
        notes.append(
            f"Market conditions: prices changed by {price:+.1f}%, with about "
            f"{offers:.1f} competitor offers per customer."
        )
    if peer_share >= 0.5:
        notes.append(
            f"{peer_share:.0%} of employees in the same role show the same decline."
        )
    if sentiment <= -0.3:
        notes.append("Recent employee feedback includes more concerns than positive comments.")
    if parts_delta > 0:
        notes.append(f"Jobs involving parts waits increased by {parts_delta:.0%} from the usual level.")
    if incomplete_delta > 0:
        notes.append(f"Incomplete incoming records increased by {incomplete_delta:.0%} from the usual level.")
    return ContextFindings(
        workload_ratio=round(ratio, 2), complexity_delta=round(cdelta, 2), overtime_hours=round(overtime, 1),
        downtime_delta=round(ddelta, 1), price_change_pct=round(price, 1), competitor_offers=round(offers, 1),
        budget_share=round(budget, 2), sentiment=sentiment, feedback_tags=tags,
        peer_deviation_share=round(peer_share, 2), parts_wait_share_delta=round(parts_delta, 3),
        incomplete_input_delta=round(incomplete_delta, 3), notes=notes)
