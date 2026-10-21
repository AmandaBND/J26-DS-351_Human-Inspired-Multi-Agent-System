
from dataclasses import dataclass, field

import numpy as np


@dataclass
class TemporalEmotionPoint:
    start_seconds: float
    end_seconds: float
    frustration_evidence: float
    satisfaction_evidence: float
    uncertainty: float
    trend: str
    evidence: list[str] = field(default_factory=list)


class TemporalEmotionFusionService:
    """
    Combine customer text cues and relative acoustic changes.

    Scores are experimental evidence indicators, not calibrated
    probabilities or validated emotion classifications.
    """

    def analyze(self, text_cues, acoustic_features):
        if not text_cues:
            return []

        text_cues = sorted(
            text_cues,
            key=lambda item: item.start_seconds,
        )

        acoustic_features = sorted(
            acoustic_features,
            key=lambda item: item.start_seconds,
        )

        energies = np.array(
            [item.rms_energy for item in acoustic_features],
            dtype=float,
        )

        energy_baseline = (
            float(np.median(energies))
            if energies.size
            else None
        )

        results = []
        previous_frustration = None

        for cue in text_cues:
            evidence = list(cue.matched_cues)

            # Start with text-based evidence.
            frustration = float(cue.frustration_score)
            satisfaction = float(cue.satisfaction_score)

            # Find the acoustic segment with the greatest
            # timestamp overlap with this customer turn.
            best_feature = None
            best_overlap = 0.0

            for feature in acoustic_features:
                overlap = max(
                    0.0,
                    min(cue.end_seconds, feature.end_seconds)
                    - max(cue.start_seconds, feature.start_seconds),
                )

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_feature = feature

            acoustic_support = 0.0

            if (
                best_feature is not None
                and energy_baseline is not None
                and energy_baseline > 1e-6
            ):
                relative_energy = (
                    best_feature.rms_energy / energy_baseline
                )

                if relative_energy >= 1.5:
                    acoustic_support = 0.15
                    evidence.append(
                        "Elevated vocal energy relative to "
                        "customer baseline"
                    )

            # Elevated energy is weak, nonspecific evidence.
            # It must not create a frustration label by itself.
            if frustration > 0:
                frustration = min(
                    1.0,
                    frustration + acoustic_support,
                )

            # Higher uncertainty when text or audio is missing.
            has_text_evidence = bool(cue.matched_cues)
            has_acoustic_evidence = best_feature is not None

            if has_text_evidence and has_acoustic_evidence:
                uncertainty = 0.35
            elif has_text_evidence or has_acoustic_evidence:
                uncertainty = 0.65
            else:
                uncertainty = 0.90

            # These are heuristic uncertainty levels,
            # not statistically calibrated confidence.
            if previous_frustration is None:
                trend = "initial"
            else:
                difference = frustration - previous_frustration

                if difference > 0.10:
                    trend = "increasing"
                elif difference < -0.10:
                    trend = "decreasing"
                else:
                    trend = "stable"

            results.append(
                TemporalEmotionPoint(
                    start_seconds=cue.start_seconds,
                    end_seconds=cue.end_seconds,
                    frustration_evidence=round(frustration, 3),
                    satisfaction_evidence=round(satisfaction, 3),
                    uncertainty=uncertainty,
                    trend=trend,
                    evidence=evidence,
                )
            )

            previous_frustration = frustration

        return results
