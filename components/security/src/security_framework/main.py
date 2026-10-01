from dataclasses import dataclass
from datetime import datetime


@dataclass
class ResearchComponent:
    name: str
    student_id: str
    phase: str
    research_question: str


def get_component_info() -> ResearchComponent:
    return ResearchComponent(
        name="Adaptive Self-Attesting Multi-Agent Security Framework",
        student_id="IT23280274",
        phase="PP1 - Standalone Research Development",
        research_question=(
            "Can software-level behavioural self-attestation and adaptive "
            "trust-weighted decision fusion maintain reliable security decisions "
            "when one or more security-monitoring agents become unreliable "
            "or compromised?"
        ),
    )


def main() -> None:
    component = get_component_info()

    
    print(component.name)
    

    print(f"Student ID : {component.student_id}")
    print(f"Phase      : {component.phase}")
    print(f"Started    : {datetime.now().isoformat(timespec='seconds')}")

    print("\nResearch Question:")
    print(component.research_question)

    print("\nStatus:")
    print("Research environment initialized successfully.")


if __name__ == "__main__":
    main()