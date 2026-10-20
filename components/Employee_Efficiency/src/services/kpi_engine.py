"""Deterministic KPI maths: benchmarks from history, 0-100 performance index, category/overall scores."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import BASELINE_YEAR, MIN_KPI_COVERAGE
from src.schemas.kpi import KPI_REGISTRY, ROLE_CATEGORY_WEIGHTS, ROLE_KPIS, Category, Role

INDEX_CENTER = 75.0   # a value exactly at the historical benchmark scores 75
INDEX_SPREAD = 12.0   # each standard deviation better/worse moves the index by 12 points


def label_for(index: float) -> str:
    """Text label so risk is never conveyed by colour alone (accessibility requirement)."""
    if index >= 85:
        return "Strong"
    if index >= 65:
        return "On target"
    if index >= 50:
        return "Watch"
    return "Concern"


def compute_benchmarks(kpi: pd.DataFrame, baseline_year: int = BASELINE_YEAR) -> pd.DataFrame:
    """Targets come from Metropolitan's own history: role-wide mean/std of the baseline year."""
    base = kpi[kpi["period"].str[:4] == str(baseline_year)]
    bench = base.groupby(["role", "kpi_code"])["value"].agg(["mean", "std"]).reset_index()
    bench["std"] = bench["std"].clip(lower=1e-6)
    return bench.rename(columns={"mean": "bench_mean", "std": "bench_std"})


def add_indices(kpi: pd.DataFrame, bench: pd.DataFrame) -> pd.DataFrame:
    df = kpi.merge(bench, on=["role", "kpi_code"], how="left")
    df["category"] = df["kpi_code"].map(lambda c: KPI_REGISTRY[c].category.value)
    higher = df["kpi_code"].map(lambda c: KPI_REGISTRY[c].higher_is_better)
    z = (df["value"] - df["bench_mean"]) / df["bench_std"]
    z = z.where(higher, -z)
    df["index"] = (INDEX_CENTER + INDEX_SPREAD * z).clip(0, 100)
    return df


def weighted_overall(cat_scores: dict[str, float], role: Role) -> float:
    weights = ROLE_CATEGORY_WEIGHTS[role]
    num = den = 0.0
    for cat, w in weights.items():
        v = cat_scores.get(cat.value)
        if v is not None and not np.isnan(v):
            num += w * v
            den += w
    return float(num / den) if den else float("nan")


def monthly_scores(kpi_idx: pd.DataFrame) -> pd.DataFrame:
    """Employee-month category scores; incomplete months have no overall composite."""
    cat = (kpi_idx.groupby(["employee_id", "role", "period", "category"])["index"].mean().reset_index())
    wide = cat.pivot_table(index=["employee_id", "role", "period"], columns="category", values="index").reset_index()
    cats = [c.value for c in Category if c.value in wide.columns]
    counts = (
        kpi_idx.groupby(["employee_id", "role", "period"])["kpi_code"]
        .nunique()
        .rename("kpi_count")
        .reset_index()
    )
    wide = wide.merge(counts, on=["employee_id", "role", "period"], how="left")

    def complete(row: pd.Series) -> bool:
        role = Role(row["role"])
        required = ROLE_CATEGORY_WEIGHTS[role]
        coverage = row["kpi_count"] / len(ROLE_KPIS[role])
        return coverage >= MIN_KPI_COVERAGE and all(
            category.value in row.index and pd.notna(row[category.value]) for category in required
        )

    complete_month = wide.apply(complete, axis=1)
    wide["overall"] = wide.apply(
        lambda row: weighted_overall({category: row.get(category, np.nan) for category in cats},
                                     Role(row["role"]))
        if complete_month.loc[row.name] else np.nan,
        axis=1,
    )
    return wide.sort_values(["employee_id", "period"]).reset_index(drop=True)
