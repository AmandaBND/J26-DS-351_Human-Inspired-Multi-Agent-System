import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.ml import (
    ReliabilityModelTrainer,
)


def main() -> None:
    data_dir = (
        PROJECT_ROOT
        / "data"
        / "benchmark"
        / "reliability"
    )

    results_dir = (
        PROJECT_ROOT
        / "results"
        / "reliability_models"
    )

    model_dir = (
        PROJECT_ROOT
        / "models"
        / "reliability"
    )

    results_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    trainer = ReliabilityModelTrainer(
        random_state=42
    )

    train_frame = trainer.load_feature_csv(
        data_dir / "train_features.csv"
    )

    validation_frame = (
        trainer.load_feature_csv(
            data_dir
            / "validation_features.csv"
        )
    )

    test_frame = trainer.load_feature_csv(
        data_dir / "test_features.csv"
    )

    (
        metrics,
        predictions,
    ) = trainer.train_and_evaluate(
        train_frame=train_frame,
        validation_frame=validation_frame,
        test_frame=test_frame,
        model_dir=model_dir,
    )

    metrics_file = (
        results_dir
        / "model_metrics.csv"
    )

    predictions_file = (
        results_dir
        / "test_predictions.csv"
    )

    metrics.to_csv(
        metrics_file,
        index=False,
    )

    predictions.to_csv(
        predictions_file,
        index=False,
    )

    best = metrics.iloc[0]

    summary = {
        "best_model_by_f1_then_auprc": (
            best["model"]
        ),
        "best_f1": float(
            best["f1"]
        ),
        "best_auprc": float(
            best["auprc"]
        ),
        "warning": (
            "These are preliminary PP1 results on a "
            "controlled synthetic reliability benchmark."
        ),
    }

    (
        results_dir
        / "summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nModel comparison:")
    print(
        metrics.to_string(
            index=False
        )
    )

    print(
        f"\nBest preliminary model: "
        f"{summary['best_model_by_f1_then_auprc']}"
    )

    # PP1 comparison plot.
    plot_frame = metrics.set_index(
        "model"
    )[
        ["f1", "auprc"]
    ]

    ax = plot_frame.plot(
        kind="bar"
    )

    ax.set_title(
        "Preliminary Monitor Reliability Model Comparison"
    )
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    ax.figure.tight_layout()

    figure_file = (
        results_dir
        / "model_comparison.png"
    )

    ax.figure.savefig(
        figure_file,
        dpi=180,
    )

    plt.close(
        ax.figure
    )

    print(
        f"\nMetrics: {metrics_file}"
    )
    print(
        f"Predictions: {predictions_file}"
    )
    print(
        f"Figure: {figure_file}"
    )


if __name__ == "__main__":
    main()
