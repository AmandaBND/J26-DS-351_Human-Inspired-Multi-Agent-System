from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    IsolationForest,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from security_framework.features import (
    MODEL_FEATURE_COLUMNS,
)


@dataclass
class TrainedReliabilityModel:
    name: str
    model: Any
    threshold: float
    feature_columns: list[str]


class ReliabilityModelTrainer:
    """
    Compare supervised and normal-only monitor-reliability baselines.

    Model input is restricted to MODEL_FEATURE_COLUMNS.
    Experiment metadata and compromise labels are never included in X.
    """

    def __init__(
        self,
        *,
        random_state: int = 42,
    ) -> None:
        self.random_state = random_state

    @staticmethod
    def load_feature_csv(
        file_path: str | Path,
    ) -> pd.DataFrame:
        frame = pd.read_csv(file_path)

        missing = [
            column
            for column in MODEL_FEATURE_COLUMNS
            if column not in frame.columns
        ]

        if missing:
            raise ValueError(
                "Feature dataset is missing columns: "
                + ", ".join(missing)
            )

        if "compromised_label" not in frame.columns:
            raise ValueError(
                "Feature dataset has no compromised_label."
            )

        return frame

    @staticmethod
    def _x_y(
        frame: pd.DataFrame,
    ) -> tuple[pd.DataFrame, np.ndarray]:
        x = frame[
            MODEL_FEATURE_COLUMNS
        ].copy()

        y = (
            frame["compromised_label"]
            .astype(int)
            .to_numpy()
        )

        return x, y

    @staticmethod
    def _select_threshold(
        y_true: np.ndarray,
        scores: np.ndarray,
    ) -> float:
        if len(np.unique(y_true)) < 2:
            return float(
                np.median(scores)
            )

        minimum = float(np.min(scores))
        maximum = float(np.max(scores))

        if minimum == maximum:
            return minimum

        thresholds = np.linspace(
            minimum,
            maximum,
            151,
        )

        best_threshold = thresholds[0]
        best_f1 = -1.0

        for threshold in thresholds:
            predicted = (
                scores >= threshold
            ).astype(int)

            score = f1_score(
                y_true,
                predicted,
                zero_division=0,
            )

            if score > best_f1:
                best_f1 = score
                best_threshold = threshold

        return float(best_threshold)

    @staticmethod
    def _metrics(
        y_true: np.ndarray,
        scores: np.ndarray,
        threshold: float,
    ) -> dict[str, float]:
        predicted = (
            scores >= threshold
        ).astype(int)

        tn, fp, fn, tp = confusion_matrix(
            y_true,
            predicted,
            labels=[0, 1],
        ).ravel()

        fpr = (
            fp / (fp + tn)
            if (fp + tn) > 0
            else 0.0
        )

        metrics = {
            "precision": precision_score(
                y_true,
                predicted,
                zero_division=0,
            ),
            "recall": recall_score(
                y_true,
                predicted,
                zero_division=0,
            ),
            "f1": f1_score(
                y_true,
                predicted,
                zero_division=0,
            ),
            "auprc": average_precision_score(
                y_true,
                scores,
            ),
            "fpr": fpr,
            "threshold": threshold,
            "test_samples": len(y_true),
        }

        if len(np.unique(y_true)) == 2:
            metrics["auroc"] = roc_auc_score(
                y_true,
                scores,
            )
        else:
            metrics["auroc"] = float("nan")

        return metrics

    def _supervised_models(
        self,
        y_train: np.ndarray,
    ) -> dict[str, Pipeline]:
        models: dict[str, Pipeline] = {
            "logistic_regression": Pipeline(
                steps=[
                    (
                        "imputer",
                        SimpleImputer(
                            strategy="median"
                        ),
                    ),
                    (
                        "scaler",
                        StandardScaler(),
                    ),
                    (
                        "classifier",
                        LogisticRegression(
                            max_iter=2000,
                            class_weight="balanced",
                            random_state=(
                                self.random_state
                            ),
                        ),
                    ),
                ]
            ),
            "random_forest": Pipeline(
                steps=[
                    (
                        "imputer",
                        SimpleImputer(
                            strategy="median"
                        ),
                    ),
                    (
                        "classifier",
                        RandomForestClassifier(
                            n_estimators=300,
                            class_weight="balanced",
                            random_state=(
                                self.random_state
                            ),
                            n_jobs=-1,
                        ),
                    ),
                ]
            ),
        }

        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise RuntimeError(
                "xgboost is required for the PP1 "
                "model comparison. Run: pip install xgboost"
            ) from exc

        negatives = max(
            1,
            int((y_train == 0).sum()),
        )
        positives = max(
            1,
            int((y_train == 1).sum()),
        )

        scale_pos_weight = (
            negatives / positives
        )

        models["xgboost"] = Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    ),
                ),
                (
                    "classifier",
                    XGBClassifier(
                        n_estimators=250,
                        max_depth=4,
                        learning_rate=0.05,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        objective="binary:logistic",
                        eval_metric="logloss",
                        scale_pos_weight=(
                            scale_pos_weight
                        ),
                        random_state=(
                            self.random_state
                        ),
                        n_jobs=-1,
                    ),
                ),
            ]
        )

        return models

    def train_and_evaluate(
        self,
        *,
        train_frame: pd.DataFrame,
        validation_frame: pd.DataFrame,
        test_frame: pd.DataFrame,
        model_dir: str | Path,
    ) -> tuple[
        pd.DataFrame,
        pd.DataFrame,
    ]:
        model_dir = Path(model_dir)
        model_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        x_train, y_train = self._x_y(
            train_frame
        )
        x_val, y_val = self._x_y(
            validation_frame
        )
        x_test, y_test = self._x_y(
            test_frame
        )

        metric_rows: list[dict] = []
        prediction_rows: list[dict] = []

        for (
            model_name,
            model,
        ) in self._supervised_models(
            y_train
        ).items():
            model.fit(
                x_train,
                y_train,
            )

            val_scores = model.predict_proba(
                x_val
            )[:, 1]

            threshold = self._select_threshold(
                y_val,
                val_scores,
            )

            test_scores = model.predict_proba(
                x_test
            )[:, 1]

            metrics = self._metrics(
                y_test,
                test_scores,
                threshold,
            )

            metrics["model"] = model_name
            metric_rows.append(metrics)

            joblib.dump(
                {
                    "model": model,
                    "threshold": threshold,
                    "feature_columns": (
                        MODEL_FEATURE_COLUMNS
                    ),
                },
                model_dir
                / f"{model_name}.joblib",
            )

            test_predictions = (
                test_scores >= threshold
            ).astype(int)

            for row_index, (
                score,
                predicted,
            ) in enumerate(
                zip(
                    test_scores,
                    test_predictions,
                )
            ):
                original = test_frame.iloc[
                    row_index
                ]

                prediction_rows.append(
                    {
                        "model": model_name,
                        "episode_id": (
                            original["episode_id"]
                        ),
                        "monitor_id": (
                            original["monitor_id"]
                        ),
                        "experiment_condition": (
                            original[
                                "experiment_condition"
                            ]
                        ),
                        "true_label": int(
                            y_test[row_index]
                        ),
                        "score": float(score),
                        "predicted_label": int(
                            predicted
                        ),
                    }
                )

        # Normal-only Isolation Forest baseline.
        imputer = SimpleImputer(
            strategy="median"
        )

        normal_train = x_train[
            y_train == 0
        ]

        if len(normal_train) < 5:
            raise ValueError(
                "Not enough normal training rows "
                "for Isolation Forest."
            )

        imputer.fit(normal_train)

        normal_matrix = imputer.transform(
            normal_train
        )

        isolation = IsolationForest(
            n_estimators=300,
            contamination="auto",
            random_state=self.random_state,
            n_jobs=-1,
        )

        isolation.fit(normal_matrix)

        val_matrix = imputer.transform(
            x_val
        )

        # Higher score means more suspicious.
        val_scores = -isolation.decision_function(
            val_matrix
        )

        threshold = self._select_threshold(
            y_val,
            val_scores,
        )

        test_matrix = imputer.transform(
            x_test
        )

        test_scores = -isolation.decision_function(
            test_matrix
        )

        metrics = self._metrics(
            y_test,
            test_scores,
            threshold,
        )

        metrics["model"] = "isolation_forest"
        metric_rows.append(metrics)

        joblib.dump(
            {
                "imputer": imputer,
                "model": isolation,
                "threshold": threshold,
                "feature_columns": (
                    MODEL_FEATURE_COLUMNS
                ),
            },
            model_dir
            / "isolation_forest.joblib",
        )

        test_predictions = (
            test_scores >= threshold
        ).astype(int)

        for row_index, (
            score,
            predicted,
        ) in enumerate(
            zip(
                test_scores,
                test_predictions,
            )
        ):
            original = test_frame.iloc[
                row_index
            ]

            prediction_rows.append(
                {
                    "model": "isolation_forest",
                    "episode_id": (
                        original["episode_id"]
                    ),
                    "monitor_id": (
                        original["monitor_id"]
                    ),
                    "experiment_condition": (
                        original[
                            "experiment_condition"
                        ]
                    ),
                    "true_label": int(
                        y_test[row_index]
                    ),
                    "score": float(score),
                    "predicted_label": int(
                        predicted
                    ),
                }
            )

        metrics_frame = pd.DataFrame(
            metric_rows
        )

        metrics_frame = metrics_frame[
            [
                "model",
                "precision",
                "recall",
                "f1",
                "auprc",
                "auroc",
                "fpr",
                "threshold",
                "test_samples",
            ]
        ].sort_values(
            by=["f1", "auprc"],
            ascending=False,
        )

        predictions_frame = pd.DataFrame(
            prediction_rows
        )

        return (
            metrics_frame,
            predictions_frame,
        )
