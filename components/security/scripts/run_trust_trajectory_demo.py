import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.trust import (
    AdaptiveTrustEstimator,
)


def main() -> None:
    config = json.loads(
        (
            PROJECT_ROOT
            / "config"
            / "trust.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    estimator = AdaptiveTrustEstimator(
        initial_trust=config[
            "initial_trust"
        ],
        alpha=config["alpha"],
        active_threshold=config[
            "thresholds"
        ]["active"],
        reduced_threshold=config[
            "thresholds"
        ]["reduced"],
        review_threshold=config[
            "thresholds"
        ]["review"],
        severe_violation_cap=config[
            "severe_violation_cap"
        ],
    )

    # Demonstration only:
    # 5 normal windows -> 5 compromised windows -> 5 recovery windows.
    observations = []

    for window in range(1, 16):
        if window <= 5:
            phase = "NORMAL"
            p_compromised = 0.08
            challenge_accuracy = 0.95
            policy_violation_rate = 0.03

        elif window <= 10:
            phase = "COMPROMISED"
            p_compromised = 0.88
            challenge_accuracy = 0.25
            policy_violation_rate = 0.70

        else:
            phase = "RECOVERY"
            p_compromised = 0.18
            challenge_accuracy = 0.90
            policy_violation_rate = 0.08

        update = estimator.update(
            monitor_id="policy-monitor",
            p_compromised=p_compromised,
            challenge_accuracy=(
                challenge_accuracy
            ),
            policy_violation_rate=(
                policy_violation_rate
            ),
        )

        observations.append(
            {
                "window": window,
                "phase": phase,
                "p_compromised": (
                    p_compromised
                ),
                "challenge_accuracy": (
                    challenge_accuracy
                ),
                "policy_violation_rate": (
                    policy_violation_rate
                ),
                "raw_reliability": (
                    update.raw_reliability
                ),
                "trust": (
                    update.current_trust
                ),
                "status": (
                    update.status.value
                ),
            }
        )

        print(
            f"Window {window:02d} "
            f"{phase:11s} "
            f"trust={update.current_trust:.3f} "
            f"status={update.status.value}"
        )

    output_dir = (
        PROJECT_ROOT
        / "results"
        / "trust"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_file = (
        output_dir
        / "trust_trajectory_demo.csv"
    )

    with csv_file.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                observations[0].keys()
            ),
        )
        writer.writeheader()
        writer.writerows(
            observations
        )

    figure, axis = plt.subplots()

    axis.plot(
        [
            item["window"]
            for item in observations
        ],
        [
            item["trust"]
            for item in observations
        ],
        marker="o",
    )

    axis.set_title(
        "Adaptive Security-Monitor Trust Trajectory"
    )
    axis.set_xlabel(
        "Observation Window"
    )
    axis.set_ylabel(
        "Trust Score"
    )
    axis.set_ylim(
        0,
        1.05,
    )

    figure.tight_layout()

    figure_file = (
        output_dir
        / "trust_trajectory_demo.png"
    )

    figure.savefig(
        figure_file,
        dpi=180,
    )

    plt.close(
        figure
    )

    print(
        f"\nCSV: {csv_file}"
    )
    print(
        f"Figure: {figure_file}"
    )


if __name__ == "__main__":
    main()
