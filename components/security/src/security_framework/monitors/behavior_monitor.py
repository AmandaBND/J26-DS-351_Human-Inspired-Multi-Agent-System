from __future__ import annotations

import csv
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from sklearn.ensemble import IsolationForest

from security_framework.models import SecurityDecision, SecurityEvent
from security_framework.monitors.base import (
    MonitorResult,
    MonitorType,
    SecurityMonitor,
)


class BehaviorAnomalyMonitor(SecurityMonitor):
    """
    Evaluates APPLICATION-agent behavior.

    This is different from the later Monitor Reliability Model,
    which evaluates the SECURITY monitors themselves.
    """

    def __init__(
        self,
        baseline_file: str | Path,
        config_file: str | Path,
        monitor_id: str = "behavior-monitor",
    ) -> None:
        super().__init__(
            monitor_id=monitor_id,
            monitor_type=MonitorType.BEHAVIOR_ANOMALY,
        )

        self.baseline_file = Path(baseline_file)
        self.config_file = Path(config_file)

        self.config = self._load_json(self.config_file)
        self.feature_order = list(self.config["feature_order"])
        self.review_threshold = float(
            self.config.get("review_threshold", 0.90)
        )
        self.block_threshold = float(
            self.config.get("block_threshold", 0.98)
        )

        if self.review_threshold > self.block_threshold:
            raise ValueError(
                "review_threshold must be <= block_threshold."
            )

        baseline_matrix = self._load_baseline_matrix(
            self.baseline_file
        )

        minimum_rows = int(
            self.config.get("minimum_baseline_rows", 20)
        )
        if len(baseline_matrix) < minimum_rows:
            raise ValueError(
                f"Behavior baseline contains {len(baseline_matrix)} "
                f"rows; at least {minimum_rows} are required."
            )

        self.model = IsolationForest(
            n_estimators=int(
                self.config.get("n_estimators", 200)
            ),
            contamination=self.config.get(
                "contamination", "auto"
            ),
            random_state=int(
                self.config.get("random_state", 42)
            ),
        )
        self.model.fit(baseline_matrix)

        self._baseline_normality_scores = list(
            self.model.decision_function(
                baseline_matrix
            )
        )

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(
                f"Behavior monitor config does not exist: {path}"
            )

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Behavior monitor config must be a JSON object."
            )
        return data

    def _load_baseline_matrix(
        self,
        path: Path,
    ) -> list[list[float]]:
        if not path.exists():
            raise FileNotFoundError(
                f"Behavior baseline does not exist: {path}"
            )

        rows: list[list[float]] = []

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ValueError(
                    "Behavior baseline CSV has no header."
                )

            missing_columns = [
                feature
                for feature in self.feature_order
                if feature not in reader.fieldnames
            ]
            if missing_columns:
                raise ValueError(
                    "Behavior baseline is missing columns: "
                    + ", ".join(missing_columns)
                )

            for row in reader:
                rows.append(
                    [
                        float(row[feature])
                        for feature in self.feature_order
                    ]
                )

        return rows

    def _extract_feature_vector(
        self,
        event: SecurityEvent,
    ) -> tuple[list[float] | None, list[str]]:
        raw_features = event.metadata.get(
            "behavior_features"
        )

        if not isinstance(raw_features, dict):
            return None, list(self.feature_order)

        missing = [
            feature
            for feature in self.feature_order
            if feature not in raw_features
        ]
        if missing:
            return None, missing

        vector: list[float] = []

        for feature in self.feature_order:
            value = raw_features[feature]

            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Behavior feature {feature!r} must be numeric."
                )

            if value < 0:
                raise ValueError(
                    f"Behavior feature {feature!r} must not be negative."
                )

            vector.append(float(value))

        return vector, []

    def _risk_from_normality_score(
        self,
        normality_score: float,
    ) -> float:
        if not self._baseline_normality_scores:
            return 0.50

        more_normal_or_equal = sum(
            baseline_score >= normality_score
            for baseline_score
            in self._baseline_normality_scores
        )

        risk = (
            more_normal_or_equal
            / len(self._baseline_normality_scores)
        )

        return max(0.0, min(1.0, float(risk)))

    def evaluate(
        self,
        event: SecurityEvent,
    ) -> MonitorResult:
        started_at = perf_counter()

        vector, missing = self._extract_feature_vector(
            event
        )

        if vector is None:
            return self._build_result(
                event=event,
                decision=SecurityDecision.REVIEW,
                risk_score=0.50,
                confidence=0.50,
                started_at=started_at,
                reason_codes=[
                    "MISSING_BEHAVIOR_FEATURES"
                ],
                metadata={
                    "missing_features": missing,
                    "feature_order": self.feature_order,
                },
            )

        normality_score = float(
            self.model.decision_function(
                [vector]
            )[0]
        )

        risk_score = self._risk_from_normality_score(
            normality_score
        )

        if risk_score >= self.block_threshold:
            decision = SecurityDecision.BLOCK
            reason = "BEHAVIOR_ANOMALY_HIGH_RISK"
        elif risk_score >= self.review_threshold:
            decision = SecurityDecision.REVIEW
            reason = "BEHAVIOR_ANOMALY_UNCERTAIN"
        else:
            decision = SecurityDecision.ALLOW
            reason = "BEHAVIOR_WITHIN_BASELINE"

        confidence = max(
            risk_score,
            1.0 - risk_score,
        )

        return self._build_result(
            event=event,
            decision=decision,
            risk_score=risk_score,
            confidence=confidence,
            started_at=started_at,
            reason_codes=[reason],
            metadata={
                "model": "IsolationForest",
                "normality_score": normality_score,
                "feature_order": self.feature_order,
                "baseline_file": str(self.baseline_file),
                "baseline_type": (
                    "synthetic_pp1_engineering_baseline"
                ),
            },
        )
