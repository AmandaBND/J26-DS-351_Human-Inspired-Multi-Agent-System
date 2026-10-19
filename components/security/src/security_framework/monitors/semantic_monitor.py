from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from security_framework.models import (
    SecurityDecision,
    SecurityEvent,
)

from security_framework.monitors.base import (
    MonitorResult,
    MonitorType,
    SecurityMonitor,
)


ClassifierCallable = Callable[..., Any]


class SemanticPromptMonitor(SecurityMonitor):
    """
    Semantic / prompt security monitor.

    The real implementation uses:
    meta-llama/Llama-Prompt-Guard-2-86M

    The model is loaded lazily so normal unit tests do not
    need to download the Hugging Face model.

    A fake classifier can also be injected during unit testing.
    """

    DEFAULT_MODEL_ID = (
        "meta-llama/Llama-Prompt-Guard-2-86M"
    )

    def __init__(
        self,
        monitor_id: str = "semantic-monitor",
        model_id: str = DEFAULT_MODEL_ID,
        review_threshold: float = 0.50,
        block_threshold: float = 0.85,
        classifier: ClassifierCallable | None = None,
    ) -> None:
        super().__init__(
            monitor_id=monitor_id,
            monitor_type=MonitorType.SEMANTIC_PROMPT,
        )

        if not 0.0 <= review_threshold <= 1.0:
            raise ValueError(
                "review_threshold must be between 0 and 1."
            )

        if not 0.0 <= block_threshold <= 1.0:
            raise ValueError(
                "block_threshold must be between 0 and 1."
            )

        if review_threshold > block_threshold:
            raise ValueError(
                "review_threshold must be "
                "<= block_threshold."
            )

        self.model_id = model_id
        self.review_threshold = review_threshold
        self.block_threshold = block_threshold

        self._classifier = classifier

    def _get_classifier(
        self,
    ) -> ClassifierCallable:
        """
        Load the Hugging Face classifier only when
        the real monitor is actually used.
        """

        if self._classifier is not None:
            return self._classifier

        try:
            from transformers import pipeline

        except ImportError as exc:
            raise RuntimeError(
                "transformers is not installed. "
                "Run: pip install -r requirements.txt"
            ) from exc

        try:
            self._classifier = pipeline(
                "text-classification",
                model=self.model_id,
            )

        except Exception as exc:
            raise RuntimeError(
                "Could not load the Prompt Guard model. "
                "If Hugging Face requires model access, "
                "accept the model license and login first."
            ) from exc

        return self._classifier

    @staticmethod
    def _extract_text(
        event: SecurityEvent,
    ) -> str:
        """
        Collect the text that should be inspected.

        We currently inspect:
        - content_summary
        - metadata.prompt_text
        - metadata.message_text
        """

        parts: list[str] = []

        if event.content_summary:
            parts.append(
                event.content_summary
            )

        prompt_text = event.metadata.get(
            "prompt_text"
        )

        if (
            isinstance(prompt_text, str)
            and prompt_text.strip()
        ):
            parts.append(
                prompt_text
            )

        message_text = event.metadata.get(
            "message_text"
        )

        if (
            isinstance(message_text, str)
            and message_text.strip()
        ):
            parts.append(
                message_text
            )

        # Use a normal space between available text fields.
        # This avoids accidental malformed multiline strings.
        return " ".join(parts).strip()

    @staticmethod
    def _normalize_label(
        label: str,
    ) -> str:
        return label.strip().upper()

    @classmethod
    def _malicious_probability_from_output(
        cls,
        output: Any,
    ) -> tuple[float, str]:
        """
        Convert Hugging Face classifier output into
        a probability of malicious prompt behaviour.

        Supported labels:
        BENIGN
        MALICIOUS

        LABEL_0 and LABEL_1 are also supported as
        defensive fallbacks.
        """

        if isinstance(output, dict):
            candidates = [output]

        elif isinstance(output, list):

            if (
                output
                and isinstance(
                    output[0],
                    list,
                )
            ):
                candidates = output[0]

            else:
                candidates = output

        else:
            raise ValueError(
                "Unsupported classifier "
                f"output type: {type(output)!r}"
            )

        candidates = [
            item
            for item in candidates
            if (
                isinstance(item, dict)
                and "label" in item
                and "score" in item
            )
        ]

        if not candidates:
            raise ValueError(
                "Classifier output does not contain "
                "label and score values."
            )

        malicious_labels = {
            "MALICIOUS",
            "JAILBREAK",
            "INJECTION",
            "LABEL_1",
        }

        benign_labels = {
            "BENIGN",
            "SAFE",
            "LABEL_0",
        }

        # First look for an explicit malicious score.
        for item in candidates:

            label = cls._normalize_label(
                str(item["label"])
            )

            score = float(
                item["score"]
            )

            if label in malicious_labels:

                score = max(
                    0.0,
                    min(
                        1.0,
                        score,
                    ),
                )

                return score, label

        # If only the top class is returned,
        # inspect that prediction.
        best = max(
            candidates,
            key=lambda item: float(
                item["score"]
            ),
        )

        label = cls._normalize_label(
            str(best["label"])
        )

        score = float(
            best["score"]
        )

        score = max(
            0.0,
            min(
                1.0,
                score,
            ),
        )

        if label in benign_labels:
            return (
                1.0 - score,
                label,
            )

        raise ValueError(
            f"Unknown classifier label: {label}. "
            "Expected BENIGN/MALICIOUS "
            "or LABEL_0/LABEL_1."
        )

    @staticmethod
    def _chunk_text(
        text: str,
        classifier: ClassifierCallable,
    ) -> list[str]:
        """
        Split long input when the classifier exposes
        a Hugging Face tokenizer.

        If no tokenizer exists, return the original
        text as one chunk.

        Prompt Guard 2 has a limited context window,
        so long inputs should not simply be truncated.
        """

        tokenizer = getattr(
            classifier,
            "tokenizer",
            None,
        )

        if tokenizer is None:
            return [text]

        try:
            token_ids = tokenizer.encode(
                text,
                add_special_tokens=False,
            )

        except Exception:
            return [text]

        max_length = getattr(
            tokenizer,
            "model_max_length",
            512,
        )

        if (
            not isinstance(
                max_length,
                int,
            )
            or max_length > 4096
        ):
            max_length = 512

        max_length = min(
            max_length,
            512,
        )

        chunk_size = max(
            32,
            max_length - 2,
        )

        overlap = min(
            32,
            chunk_size // 4,
        )

        if len(token_ids) <= chunk_size:
            return [text]

        chunks: list[str] = []

        start = 0

        while start < len(token_ids):

            end = min(
                start + chunk_size,
                len(token_ids),
            )

            chunk_ids = token_ids[
                start:end
            ]

            chunk_text = tokenizer.decode(
                chunk_ids,
                skip_special_tokens=True,
            )

            chunks.append(
                chunk_text
            )

            if end >= len(token_ids):
                break

            start = end - overlap

        return chunks

    def evaluate(
        self,
        event: SecurityEvent,
    ) -> MonitorResult:
        """
        Inspect one SecurityEvent and return a
        normalized MonitorResult.
        """

        started_at = perf_counter()

        text = self._extract_text(
            event
        )

        if not text:

            return self._build_result(
                event=event,
                decision=SecurityDecision.REVIEW,
                risk_score=0.50,
                confidence=0.50,
                started_at=started_at,
                reason_codes=[
                    "NO_TEXT_AVAILABLE"
                ],
                metadata={
                    "model_id": self.model_id,
                },
            )

        classifier = (
            self._get_classifier()
        )

        chunks = self._chunk_text(
            text,
            classifier,
        )

        highest_risk = 0.0

        labels: list[str] = []

        for chunk in chunks:

            output = classifier(
                chunk,
                truncation=True,
            )

            (
                malicious_risk,
                label,
            ) = (
                self
                ._malicious_probability_from_output(
                    output
                )
            )

            highest_risk = max(
                highest_risk,
                malicious_risk,
            )

            labels.append(
                label
            )

        if (
            highest_risk
            >= self.block_threshold
        ):
            decision = (
                SecurityDecision.BLOCK
            )

            reason = (
                "PROMPT_ATTACK_HIGH_RISK"
            )

        elif (
            highest_risk
            >= self.review_threshold
        ):
            decision = (
                SecurityDecision.REVIEW
            )

            reason = (
                "PROMPT_ATTACK_UNCERTAIN"
            )

        else:
            decision = (
                SecurityDecision.ALLOW
            )

            reason = (
                "PROMPT_ATTACK_LOW_RISK"
            )

        confidence = max(
            highest_risk,
            1.0 - highest_risk,
        )

        return self._build_result(
            event=event,
            decision=decision,
            risk_score=highest_risk,
            confidence=confidence,
            started_at=started_at,
            reason_codes=[
                reason
            ],
            metadata={
                "model_id": self.model_id,
                "classifier_labels": labels,
                "chunks_scanned": len(
                    chunks
                ),
                "review_threshold": (
                    self.review_threshold
                ),
                "block_threshold": (
                    self.block_threshold
                ),
            },
        )