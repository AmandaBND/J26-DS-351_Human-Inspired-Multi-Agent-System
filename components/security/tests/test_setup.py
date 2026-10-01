import sys
from pathlib import Path


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PROJECT_SRC))


from security_framework.main import get_component_info


def test_component_information():
    component = get_component_info()

    assert component.student_id == "IT23280274"
    assert "Self-Attesting" in component.name
    assert "trust-weighted" in component.research_question.lower()