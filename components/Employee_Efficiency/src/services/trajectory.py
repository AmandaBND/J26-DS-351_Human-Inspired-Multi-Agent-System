"""Three-phase state machine, checkpoint maths, projection and deviation detection.

Phases (by the last CLOSED month, `as_of`):
  PRE_MID_YEAR   : Jan-May   -> mid-year checkpoint is still a projection
  POST_MID_YEAR  : Jun-Nov   -> mid-year confirmed, full-year projected
  POST_FULL_YEAR : Dec       -> both checkpoints confirmed
Every point carries a confirmed/projected label.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.schemas.assessment import Checkpoint, DeviationResult, Trajectory, TrajectoryPoint
from src.schemas.kpi import DataStatus, Phase

DEVIATION_DROP = 6.0       # index points below own baseline (recent 3-month mean)
MONTH_BELOW_MARGIN = 4.0   # a month counts as 'below' if > 4 points under baseline
PROJECTION_DAMPING = 0.5   # trend is damped: we do not extrapolate raw slopes


def determine_phase(as_of: str) -> Phase:
    m = int(as_of[5:7])
    if m == 12:
        return Phase.POST_FULL_YEAR
    return Phase.POST_MID_YEAR if m >= 6 else Phase.PRE_MID_YEAR


def cycle_months(year: int) -> list[str]:
    return [f"{year}-{m:02d}" for m in range(1, 13)]


def _shift(period: str, n: int) -> str:
    i = int(period[:4]) * 12 + int(period[5:]) - 1 + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def project(values: np.ndarray, horizon: int) -> list[float]:
    """Damped linear projection from the last <=6 confirmed months."""
    y = values[-6:]
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1) if len(y) >= 3 else (0.0, float(np.mean(y)))
    level = intercept + slope * (len(y) - 1)
    return [float(np.clip(level + PROJECTION_DAMPING * slope * k, 0, 100)) for k in range(1, horizon + 1)]


def _checkpoint(name: str, months: list[str], scores: dict[str, float], data_through: str) -> Checkpoint:
    vals = [scores[m] for m in months if m in scores]
    n_conf = sum(1 for m in months if m <= data_through and m in scores)
    n_proj = sum(1 for m in months if m > data_through and m in scores)
    status = "confirmed" if n_proj == 0 else ("projected" if n_conf == 0 else "partly projected")
    return Checkpoint(name=name, score=round(float(np.mean(vals)), 1) if vals else None,
                      status=status, n_confirmed=n_conf, n_projected=n_proj)


def build_trajectory(overall: pd.Series, baseline: float, as_of: str) -> Trajectory:
    """Project from the employee's last complete month, including months before `as_of`."""
    overall = overall.dropna().sort_index()
    year = int(as_of[:4])
    phase = determine_phase(as_of)
    data_through = str(overall.index[-1]) if len(overall) else ""
    confirmed = {str(p): float(v) for p, v in overall.items()}

    year_end = f"{year}-12"
    through = data_through or as_of
    horizon = int(year_end[:4]) * 12 + 12 - (
        int(through[:4]) * 12 + int(through[5:7]))
    proj_vals = project(overall.values, horizon) if horizon > 0 else []
    projected = {_shift(through, k + 1): v for k, v in enumerate(proj_vals)}
    all_scores = {**confirmed, **projected}

    chart_from = _shift(as_of, -14)
    points = [TrajectoryPoint(period=p, score=round(v, 1),
                              status=DataStatus.CONFIRMED if p <= through else DataStatus.PROJECTED)
              for p, v in sorted(all_scores.items()) if p >= chart_from]

    months = cycle_months(year)
    mid = _checkpoint("Mid-year", months[:6], all_scores, through)
    full = _checkpoint("Full-year", months, all_scores, through)

    current = mid if phase != Phase.POST_FULL_YEAR else full
    prev_name = prev_val = None
    if phase == Phase.POST_FULL_YEAR:
        prev_name, prev_val = "Mid-year", mid.score
    else:
        prev = [confirmed[m] for m in cycle_months(year - 1) if m in confirmed]
        if len(prev) == 12:
            prev_name, prev_val = f"{year - 1} full-year", float(np.mean(prev))
    cur_score = current.score if current.score is not None else baseline
    recent_score = float(overall.iloc[-3:].mean())
    return Trajectory(
        phase=phase, cycle_year=year, points=points, mid_year=mid, full_year=full,
        baseline_score=round(baseline, 1), delta_vs_baseline=round(recent_score - baseline, 1),
        previous_checkpoint_name=prev_name,
        delta_vs_previous=round(cur_score - prev_val, 1) if prev_val is not None else None)


def detect_deviation(overall: pd.Series, baseline: float) -> DeviationResult:
    overall = overall.dropna().sort_index()
    recent = overall.iloc[-3:]
    if len(recent) < 3 or int(
        (pd.Period(str(recent.index[-1]), freq="M") - pd.Period(str(recent.index[0]), freq="M")).n
    ) > 3:
        return DeviationResult(
            is_deviating=False, severity="none", drop=0.0, slope_per_month=0.0, months_below=0,
        )
    drop = baseline - float(recent.mean())
    months_below = int((recent < baseline - MONTH_BELOW_MARGIN).sum())
    last6 = overall.iloc[-6:].values
    slope = float(np.polyfit(np.arange(len(last6)), last6, 1)[0]) if len(last6) >= 3 else 0.0
    is_dev = drop >= DEVIATION_DROP and months_below >= 2
    if not is_dev:
        severity = "none"
    elif drop >= 18:
        severity = "high"
    elif drop >= 10:
        severity = "medium"
    else:
        severity = "low"
    return DeviationResult(is_deviating=is_dev, severity=severity, drop=round(drop, 1),
                           slope_per_month=round(slope, 2), months_below=months_below)
