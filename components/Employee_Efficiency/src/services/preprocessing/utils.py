"""Shared parsing, normalization, and quality logging for preprocessing."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import RAW_DIR
from src.database.models import DataQualityLog, SessionLocal


DATETIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")


def read_raw(filename: str) -> pd.DataFrame:
    """Read one CSV as strings while preserving blanks and leading zeroes."""
    path = RAW_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required source file is missing: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _parse_one(value: Any, formats: tuple[str, ...]) -> pd.Timestamp | pd.NaT:
    if value is None or pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT
    for fmt in formats:
        try:
            return pd.Timestamp(datetime.strptime(text, fmt))
        except ValueError:
            continue
    return pd.NaT


def parse_datetime(series: pd.Series) -> pd.Series:
    """Parse mixed supported timestamp formats cell by cell; invalid values become NaT."""
    return series.map(lambda value: _parse_one(value, DATETIME_FORMATS))


def parse_date(series: pd.Series) -> pd.Series:
    """Parse supported date-only formats cell by cell; invalid values become NaT."""
    return series.map(lambda value: _parse_one(value, DATE_FORMATS))


def norm_emp_no(value: Any) -> str | Any:
    """Normalize a 1-6 digit employee number to six digits or return pandas NA."""
    if value is None or pd.isna(value):
        return pd.NA
    text = str(value).strip()
    return text.zfill(6) if re.fullmatch(r"\d{1,6}", text) else pd.NA


def to_bool(value: Any) -> bool | Any:
    """Convert common yes/no spellings to booleans; unknown values become pandas NA."""
    if value is None or pd.isna(value):
        return pd.NA
    text = str(value).strip().casefold()
    if text in {"y", "yes", "1", "true"}:
        return True
    if text in {"n", "no", "0", "false"}:
        return False
    return pd.NA


def parse_period(value: Any) -> str | Any:
    """Normalize YYYY-MM or Mon-YYYY text to a YYYY-MM period."""
    if value is None or pd.isna(value):
        return pd.NA
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text
    try:
        return datetime.strptime(text, "%b-%Y").strftime("%Y-%m")
    except ValueError:
        return pd.NA


class QualityLogger:
    """Collect aggregate cleaning outcomes and persist safe, row-free audit entries."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.row_counts: dict[str, tuple[int, int]] = {}

    def record(
        self,
        stage: str,
        source_file: str,
        rule: str,
        rows_before: int,
        rows_after: int,
        rows_affected: int,
        action: str,
        detail: str = "",
    ) -> None:
        """Record one aggregate transformation without source row contents."""
        self.entries.append({
            "stage": stage,
            "source_file": source_file,
            "rule": rule,
            "rows_before": int(rows_before),
            "rows_after": int(rows_after),
            "rows_affected": int(rows_affected),
            "action": action,
            "detail": detail,
        })

    def note_file_counts(self, filename: str, before: int, after: int) -> None:
        """Store total row counts before and after cleaning for reporting."""
        self.row_counts[filename] = (int(before), int(after))
        self.record(
            "cleaning", filename, "file_total_rows", before, after, abs(before - after),
            "clean", "Aggregate source row counts.",
        )

    def write_db(self, run_id: str) -> None:
        """Persist collected aggregate quality outcomes to the current database."""
        with SessionLocal() as session:
            session.add_all([
                DataQualityLog(run_id=run_id, **entry)
                for entry in self.entries
            ])
            session.commit()

    def render_markdown(self, path: Path) -> None:
        """Write aggregate before/after counts and cleaning rules to a Markdown report."""
        lines = [
            "# Data quality report",
            "",
            "Generated from aggregate preprocessing counts. No employee identifiers or row-level values are included.",
            "",
            "## Row counts",
            "",
            "| Source file | Before | After |",
            "|---|---:|---:|",
        ]
        for filename, (before, after) in sorted(self.row_counts.items()):
            lines.append(f"| {filename} | {before} | {after} |")
        lines.extend([
            "",
            "## Cleaning actions",
            "",
            "| Stage | Source file | Rule | Rows affected | Action | Detail |",
            "|---|---|---|---:|---|---|",
        ])
        for entry in self.entries:
            detail = entry["detail"].replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {entry['stage']} | {entry['source_file']} | {entry['rule']} | "
                f"{entry['rows_affected']} | {entry['action']} | {detail} |"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def log_value_changes(
    logger: QualityLogger,
    source_file: str,
    rule: str,
    before: int,
    changed: int,
    detail: str = "",
) -> None:
    """Record an in-place normalization that does not change the row count."""
    if changed:
        logger.record("cleaning", source_file, rule, before, before, changed, "normalize", detail)
