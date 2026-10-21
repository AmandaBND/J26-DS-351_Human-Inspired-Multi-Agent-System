from pathlib import Path
import re


class PolicyRAGAgent:
    """Retrieve evidence from synthetic AMC research policies."""

    def __init__(self, policy_dir=None):
        if policy_dir is None:
            policy_dir = (
                Path(__file__).resolve().parents[3]
                / "knowledge_base"
                / "amc_policies"
            )

        self.policy_dir = Path(policy_dir)

    def retrieve(self, query: str, top_k: int = 3):
        if not self.policy_dir.exists():
            raise FileNotFoundError(
                f"Policy directory not found: {self.policy_dir}"
            )

        query_terms = set(
            re.findall(r"[a-z0-9]+", query.lower())
        )

        results = []

        for path in sorted(self.policy_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8-sig")

            lines = [
                line.strip()
                for line in content.splitlines()
                if line.strip()
            ]

            title = lines[0].removeprefix("# ").strip()
            policy_id = title.split(":")[0]

            # Divide policy into small evidence passages.
            paragraphs = [
                p.strip().replace("\n", " ")
                for p in re.split(r"\n\s*\n", content)
                if p.strip()
            ]

            for passage in paragraphs:
                passage_terms = set(
                    re.findall(r"[a-z0-9]+", passage.lower())
                )

                overlap = query_terms & passage_terms
                score = len(overlap)

                if score == 0:
                    continue

                results.append(
                    {
                        "policy_id": policy_id,
                        "document": path.name,
                        "title": title,
                        "passage": passage,
                        "score": score,
                        "source_type": "synthetic_research_policy",
                    }
                )

        results.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return results[:top_k]