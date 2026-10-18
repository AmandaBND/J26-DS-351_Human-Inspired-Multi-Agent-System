from __future__ import annotations

import json
import re
from pathlib import Path

import joblib
import pandas as pd

from security_framework.features import MODEL_FEATURE_COLUMNS
from security_framework.fusion import FusionInput, SecurityDecisionFusion
from security_framework.history import MonitorDecisionLogger
from security_framework.models import SecurityDecision
from security_framework.trust import AdaptiveTrustEstimator


STRATEGIES = [
    "single_guard",
    "equal_majority",
    "static_weighting",
    "adaptive_trust_weighting",
]


def calculate_system_metrics(frame: pd.DataFrame) -> dict[str, float]:
    """Calculate final-decision metrics from event-level results."""
    if frame.empty:
        return {
            "events": 0,
            "final_decision_accuracy": 0.0,
            "attack_success_rate": 0.0,
            "false_block_rate": 0.0,
            "review_rate": 0.0,
        }

    accuracy = (
        frame["final_decision"] == frame["expected_decision"]
    ).mean()

    expected_block = frame[frame["expected_decision"] == "BLOCK"]
    attack_success = (
        (expected_block["final_decision"] == "ALLOW").mean()
        if len(expected_block)
        else 0.0
    )

    expected_allow = frame[frame["expected_decision"] == "ALLOW"]
    false_block = (
        (expected_allow["final_decision"] == "BLOCK").mean()
        if len(expected_allow)
        else 0.0
    )

    review_rate = (frame["final_decision"] == "REVIEW").mean()

    return {
        "events": int(len(frame)),
        "final_decision_accuracy": float(accuracy),
        "attack_success_rate": float(attack_success),
        "false_block_rate": float(false_block),
        "review_rate": float(review_rate),
    }


class SystemResilienceEvaluator:
    """
    Held-out system evaluation.

    Hidden compromise labels are used only to group/report results.
    They are never passed into the reliability model or trust update.
    """

    def __init__(
        self,
        *,
        feature_file: str | Path,
        decision_log: str | Path,
        model_metrics_file: str | Path,
        model_dir: str | Path,
        trust_config_file: str | Path,
        fusion_config_file: str | Path,
        evidence_mode: str = "full",
    ) -> None:
        self.feature_file = Path(feature_file)
        self.decision_log = Path(decision_log)
        self.model_metrics_file = Path(model_metrics_file)
        self.model_dir = Path(model_dir)
        self.trust_config_file = Path(trust_config_file)
        self.fusion_config_file = Path(fusion_config_file)
        self.evidence_mode = evidence_mode

        if evidence_mode not in {
            "full",
            "model_only",
            "no_challenge",
            "no_policy",
        }:
            raise ValueError(f"Unsupported evidence mode: {evidence_mode}")

    @staticmethod
    def _episode_number(episode_id: str) -> int:
        match = re.search(r"-(\d+)$", episode_id)
        return int(match.group(1)) if match else 10**9

    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Missing config: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _best_supervised_model(self):
        if not self.model_metrics_file.exists():
            raise FileNotFoundError(
                "Missing model_metrics.csv. Run train_reliability_models.py first."
            )

        metrics = pd.read_csv(self.model_metrics_file)
        supervised = metrics[metrics["model"] != "isolation_forest"].copy()

        if supervised.empty:
            raise ValueError("No supervised reliability model is available.")

        supervised = supervised.sort_values(
            by=["f1", "auprc"],
            ascending=False,
        )
        name = str(supervised.iloc[0]["model"])
        model_file = self.model_dir / f"{name}.joblib"

        if not model_file.exists():
            raise FileNotFoundError(
                f"Missing trained model: {model_file}\n"
                "Run train_reliability_models.py first."
            )

        bundle = joblib.load(model_file)
        return name, bundle["model"]

    @staticmethod
    def _optional(value) -> float | None:
        return None if pd.isna(value) else float(value)

    def _trust_estimator(self) -> AdaptiveTrustEstimator:
        config = self._read_json(self.trust_config_file)
        weights = config["weights"]
        thresholds = config["thresholds"]

        return AdaptiveTrustEstimator(
            initial_trust=float(config["initial_trust"]),
            alpha=float(config["alpha"]),
            model_weight=float(weights["model_reliability"]),
            challenge_weight=float(weights["challenge_accuracy"]),
            policy_weight=float(weights["policy_integrity"]),
            active_threshold=float(thresholds["active"]),
            reduced_threshold=float(thresholds["reduced"]),
            review_threshold=float(thresholds["review"]),
            severe_violation_cap=float(config["severe_violation_cap"]),
        )

    def _fusion(self):
        config = self._read_json(self.fusion_config_file)
        fusion = SecurityDecisionFusion(
            review_threshold=float(config["review_threshold"]),
            block_threshold=float(config["block_threshold"]),
        )
        return fusion, config

    def _evidence(self, row: pd.Series) -> tuple[float | None, float | None]:
        challenge = self._optional(row["challenge_accuracy"])
        policy = self._optional(row["policy_violation_rate"])

        if self.evidence_mode == "model_only":
            return None, None
        if self.evidence_mode == "no_challenge":
            return None, policy
        if self.evidence_mode == "no_policy":
            return challenge, None
        return challenge, policy

    def evaluate(self):
        if not self.feature_file.exists():
            raise FileNotFoundError(
                "Missing test_features.csv. Run generate_reliability_benchmark.py first."
            )

        features = pd.read_csv(self.feature_file)
        missing = [
            feature for feature in MODEL_FEATURE_COLUMNS
            if feature not in features.columns
        ]
        if missing:
            raise ValueError("Missing model features: " + ", ".join(missing))

        model_name, model = self._best_supervised_model()
        features = features.copy()
        features["p_compromised"] = model.predict_proba(
            features[MODEL_FEATURE_COLUMNS]
        )[:, 1]

        records = MonitorDecisionLogger(self.decision_log).read_all()
        if not records:
            raise ValueError("Held-out decision log is empty.")

        decisions = pd.DataFrame(
            [
                {
                    "episode_id": record.episode_id,
                    "event_id": record.event_id,
                    "monitor_id": record.monitor_id,
                    "decision": record.monitor_decision.value,
                    "risk_score": record.risk_score,
                    "expected_decision": record.expected_event_decision.value,
                    "attack_type": record.attack_type,
                }
                for record in records
            ]
        )

        fusion, fusion_config = self._fusion()
        trust = self._trust_estimator()

        event_rows = []
        trust_rows = []

        episode_ids = sorted(
            features["episode_id"].unique(),
            key=self._episode_number,
        )

        for episode_id in episode_ids:
            episode_features = features[
                features["episode_id"] == episode_id
            ].copy()

            if episode_features.empty:
                continue

            condition = str(
                episode_features.iloc[0]["experiment_condition"]
            )
            compromised_count = int(
                episode_features["compromised_label"].astype(int).sum()
            )

            current_trust = {}

            for _, row in episode_features.iterrows():
                challenge, policy = self._evidence(row)

                update = trust.update(
                    monitor_id=str(row["monitor_id"]),
                    p_compromised=float(row["p_compromised"]),
                    challenge_accuracy=challenge,
                    policy_violation_rate=policy,
                )

                monitor_id = str(row["monitor_id"])
                current_trust[monitor_id] = update.current_trust

                trust_rows.append(
                    {
                        "episode_id": episode_id,
                        "experiment_condition": condition,
                        "compromised_count": compromised_count,
                        "monitor_id": monitor_id,
                        "true_compromised_label": int(
                            row["compromised_label"]
                        ),
                        "p_compromised": float(row["p_compromised"]),
                        "trust": update.current_trust,
                        "trust_status": update.status.value,
                        "evidence_mode": self.evidence_mode,
                    }
                )

            episode_decisions = decisions[
                decisions["episode_id"] == episode_id
            ]

            for event_id, group in episode_decisions.groupby("event_id"):
                inputs = [
                    FusionInput(
                        monitor_id=str(record["monitor_id"]),
                        decision=SecurityDecision(record["decision"]),
                        risk_score=float(record["risk_score"]),
                        trust_score=float(
                            current_trust.get(
                                str(record["monitor_id"]),
                                0.0,
                            )
                        ),
                    )
                    for _, record in group.iterrows()
                ]

                expected = str(group.iloc[0]["expected_decision"])
                attack_type = str(group.iloc[0]["attack_type"])

                results = [
                    fusion.single_guard(
                        inputs,
                        guard_id=fusion_config["single_guard_id"],
                    ),
                    fusion.equal_majority(inputs),
                    fusion.static_weighting(
                        inputs,
                        static_weights=fusion_config["static_weights"],
                    ),
                    fusion.adaptive_trust_weighting(inputs),
                ]

                for result in results:
                    event_rows.append(
                        {
                            "episode_id": episode_id,
                            "event_id": event_id,
                            "experiment_condition": condition,
                            "compromised_count": compromised_count,
                            "attack_type": attack_type,
                            "strategy": result.strategy,
                            "expected_decision": expected,
                            "final_decision": result.decision.value,
                            "final_risk": result.final_risk,
                            "evidence_mode": self.evidence_mode,
                        }
                    )

        event_frame = pd.DataFrame(event_rows)
        trust_frame = pd.DataFrame(trust_rows)

        metric_rows = []

        for strategy in STRATEGIES:
            subset = event_frame[event_frame["strategy"] == strategy]

            metric_rows.append(
                {
                    "strategy": strategy,
                    "compromised_count": "ALL",
                    "evidence_mode": self.evidence_mode,
                    **calculate_system_metrics(subset),
                }
            )

            for count in sorted(subset["compromised_count"].unique()):
                count_subset = subset[
                    subset["compromised_count"] == count
                ]
                metric_rows.append(
                    {
                        "strategy": strategy,
                        "compromised_count": int(count),
                        "evidence_mode": self.evidence_mode,
                        **calculate_system_metrics(count_subset),
                    }
                )

        metrics = pd.DataFrame(metric_rows)

        metadata = {
            "probability_model": model_name,
            "evidence_mode": self.evidence_mode,
            "episode_count": len(episode_ids),
            "event_result_rows": len(event_frame),
            "warning": (
                "Preliminary PP1 results on a controlled held-out benchmark."
            ),
        }

        return event_frame, metrics, trust_frame, metadata
