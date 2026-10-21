"""Pseudonymize source employee numbers before persisting derived records."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import PRIVATE_DIR


def build_map(employees: pd.DataFrame, path: Path | None = None) -> dict[str, str]:
    """Assign stable EMP codes by sorted employee number and write the private mapping."""
    ids = sorted(set(employees["employee_no"].dropna().astype(str)))
    if len(ids) != len(employees):
        raise ValueError("Employee source contains missing or duplicate normalized employee numbers.")
    mapping = {employee_no: f"EMP-{index:03d}" for index, employee_no in enumerate(ids, start=1)}
    target = path or PRIVATE_DIR / "pseudonym_map.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"employee_no": employee_no, "code": code} for employee_no, code in mapping.items()]
    ).to_csv(target, index=False)
    return mapping


def apply_map(df: pd.DataFrame, columns: tuple[str, ...] | list[str], mapping: dict[str, str]) -> pd.DataFrame:
    """Return a copy with employee-number columns replaced by pseudonymous codes."""
    result = df.copy()
    for column in columns:
        if column in result.columns:
            result[column] = result[column].map(mapping).astype("string")
    return result
