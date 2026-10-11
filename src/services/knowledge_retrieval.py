from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_PATH = (
    PROJECT_ROOT
    / "data"
    / "knowledge_base"
    / "resolution_guidelines.md"
)


def retrieve_guidelines(category: str) -> str:
    """
    Retrieve relevant policy sections for a complaint.

    This is a simple category-based retriever.
    We can later replace it with vector-based RAG.
    """

    if not KNOWLEDGE_PATH.exists():
        raise FileNotFoundError(
            f"Knowledge base not found: {KNOWLEDGE_PATH}"
        )

    content = KNOWLEDGE_PATH.read_text(
        encoding="utf-8"
    )

    sections = content.split("\n## ")

    relevant_sections = []

    # Include the document introduction.
    relevant_sections.append(sections[0])

    for section in sections[1:]:

        heading = section.split("\n", 1)[0].strip()

        if heading.lower() in {
            category.lower(),
            "priority and escalation",
            "customer communication",
        }:
            relevant_sections.append(
                "## " + section
            )

    if len(relevant_sections) == 1:
        raise ValueError(
            f"No matching guidelines for category: {category}"
        )

    return "\n\n".join(relevant_sections)