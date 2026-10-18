from __future__ import annotations

from dataclasses import dataclass

import joblib
import pandas as pd

from security_framework.features import MODEL_FEATURE_COLUMNS
from security_framework.trust import AdaptiveTrustEstimator


@dataclass(frozen=True)
class DynamicRecoverySummary:
    detection_delay_windows: int | None
    recovery_delay_windows: int | None
    minimum_trust: float
    final_trust: float


def first_non_active_delay(
    frame: pd.DataFrame,
    *,
    phase: str,
) -> int | None:
    subset = frame[frame["phase"] == phase].reset_index(drop=True)
    for index, row in subset.iterrows():
        if row["trust_status"] != "ACTIVE":
            return int(index + 1)
    return None


def first_active_delay(
    frame: pd.DataFrame,
    *,
    phase: str,
) -> int | None:
    subset = frame[frame["phase"] == phase].reset_index(drop=True)
    for index, row in subset.iterrows():
        if row["trust_status"] == "ACTIVE":
            return int(index + 1)
    return None


class DynamicRecoveryExperiment:
    """NORMAL -> COMPROMISED -> RECOVERY temporal trust experiment."""

    def __init__(
        self,
        *,
        model_file,
        trust_estimator: AdaptiveTrustEstimator,
    ) -> None:
        bundle = joblib.load(model_file)
        self.model = bundle["model"]
        self.trust_estimator = trust_estimator

    @staticmethod
    def _representative_row(frame: pd.DataFrame) -> pd.Series:
        return frame[MODEL_FEATURE_COLUMNS].median(numeric_only=True)

    def _probability(self, row: pd.Series) -> float:
        one_row = pd.DataFrame(
            [{feature: row[feature] for feature in MODEL_FEATURE_COLUMNS}]
        )
        return float(self.model.predict_proba(one_row)[0, 1])

    @staticmethod
    def _optional(value) -> float | None:
        return None if pd.isna(value) else float(value)

    def run(
        self,
        *,
        test_features: pd.DataFrame,
        monitor_id: str = "policy-monitor",
        compromise_condition: str = "FALSE_ALLOW",
        normal_windows: int = 5,
        compromised_windows: int = 7,
        recovery_windows: int = 7,
    ):
        monitor_rows = test_features[
            test_features["monitor_id"] == monitor_id
        ].copy()

        normal_rows = monitor_rows[
            monitor_rows["compromised_label"] == 0
        ].copy()

        compromised_rows = monitor_rows[
            (monitor_rows["compromised_label"] == 1)
            & (
                monitor_rows["experiment_condition"]
                == compromise_condition
            )
        ].copy()

        if normal_rows.empty:
            raise ValueError("No held-out normal rows are available.")
        if compromised_rows.empty:
            raise ValueError(
                f"No held-out {compromise_condition} rows exist for {monitor_id}."
            )

        normal = self._representative_row(normal_rows)
        compromised = self._representative_row(compromised_rows)

        sequence = (
            [("NORMAL", normal)] * normal_windows
            + [("COMPROMISED", compromised)] * compromised_windows
            + [("RECOVERY", normal)] * recovery_windows
        )

        rows = []

        for window, (phase, row) in enumerate(sequence, start=1):
            p_compromised = self._probability(row)

            update = self.trust_estimator.update(
                monitor_id=monitor_id,
                p_compromised=p_compromised,
                challenge_accuracy=self._optional(
                    row["challenge_accuracy"]
                ),
                policy_violation_rate=self._optional(
                    row["policy_violation_rate"]
                ),
            )

            rows.append(
                {
                    "window": window,
                    "phase": phase,
                    "p_compromised": p_compromised,
                    "challenge_accuracy": row["challenge_accuracy"],
                    "policy_violation_rate": row["policy_violation_rate"],
                    "raw_reliability": update.raw_reliability,
                    "trust": update.current_trust,
                    "trust_status": update.status.value,
                }
            )

        frame = pd.DataFrame(rows)

        summary = DynamicRecoverySummary(
            detection_delay_windows=first_non_active_delay(
                frame,
                phase="COMPROMISED",
            ),
            recovery_delay_windows=first_active_delay(
                frame,
                phase="RECOVERY",
            ),
            minimum_trust=float(frame["trust"].min()),
            final_trust=float(frame.iloc[-1]["trust"]),
        )

        return frame, summary
