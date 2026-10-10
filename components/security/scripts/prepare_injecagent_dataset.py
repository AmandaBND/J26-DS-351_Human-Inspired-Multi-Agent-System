import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.datasets import InjecAgentAdapter


def get_git_commit(
    repository_root: Path,
) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository_root),
                "rev-parse",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "UNKNOWN"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a local InjecAgent clone "
            "into SecurityEvent JSONL files."
        )
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=(
            PROJECT_ROOT
            / "external"
            / "InjecAgent"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data"
            / "public"
            / "injecagent"
        ),
    )

    args = parser.parse_args()

    source_root = args.source.resolve()
    data_dir = source_root / "data"

    if not data_dir.exists():
        raise FileNotFoundError(
            "InjecAgent data directory was not found. "
            "Clone it first with:\n"
            "git clone "
            "https://github.com/uiuc-kang-lab/"
            "InjecAgent.git external/InjecAgent"
        )

    adapter = InjecAgentAdapter()

    mappings = [
        (
            "test_cases_dh_base.json",
            "direct_harm",
            "base",
        ),
        (
            "test_cases_dh_enhanced.json",
            "direct_harm",
            "enhanced",
        ),
        (
            "test_cases_ds_base.json",
            "data_stealing",
            "base",
        ),
        (
            "test_cases_ds_enhanced.json",
            "data_stealing",
            "enhanced",
        ),
    ]

    summary: dict[str, int | str] = {}

    for filename, family, setting in mappings:
        input_file = data_dir / filename

        if not input_file.exists():
            print(
                f"Skipping missing file: {input_file}"
            )
            continue

        events = adapter.convert_attack_records(
            input_file,
            attack_family=family,
            setting=setting,
        )

        output_file = (
            args.output
            / filename.replace(
                ".json",
                ".jsonl",
            )
        )

        adapter.write_jsonl(
            events,
            output_file,
        )

        summary[filename] = len(events)

    user_cases = data_dir / "user_cases.jsonl"

    if user_cases.exists():
        benign_events = (
            adapter.convert_benign_user_cases(
                user_cases
            )
        )

        adapter.write_jsonl(
            benign_events,
            args.output / "benign_user_cases.jsonl",
        )

        summary["benign_user_cases"] = len(
            benign_events
        )

    provenance = {
        "dataset": "InjecAgent",
        "repository": (
            "https://github.com/uiuc-kang-lab/"
            "InjecAgent"
        ),
        "source_commit": get_git_commit(
            source_root
        ),
        "local_source_path": str(source_root),
        "converted_record_counts": summary,
        "note": (
            "Raw public benchmark repository is not "
            "committed to this research repository."
        ),
    }

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    provenance_file = (
        args.output
        / "provenance.json"
    )

    provenance_file.write_text(
        json.dumps(
            provenance,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            provenance,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
