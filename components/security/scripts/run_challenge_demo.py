import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.attestation import (
    ChallengeRunner,
    load_challenge_bank,
)
from security_framework.experiment import ControlledMonitorExecutor
from security_framework.models import (
    AgentState,
    MonitorBehaviorMode,
    MonitorConfig,
)
from security_framework.monitors import PolicyToolMonitor


OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "attestation"
    / "challenge_demo.jsonl"
)


def run_episode(
    *,
    episode_id: str,
    config: MonitorConfig,
    runner: ChallengeRunner,
    challenges,
) -> None:
    monitor = PolicyToolMonitor(
        PROJECT_ROOT / "config" / "policies.json"
    )
    executor = ControlledMonitorExecutor(
        monitor,
        config,
    )

    results = runner.run_all(
        episode_id=episode_id,
        challenges=challenges,
        executor=executor,
    )

    correct = sum(
        result.is_correct
        for result in results
    )
    total = len(results)
    accuracy = correct / total if total else 0.0

    print(
        f"{episode_id}: "
        f"{correct}/{total} correct "
        f"(challenge_accuracy={accuracy:.2f})"
    )


def main() -> None:
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    challenges = load_challenge_bank(
        PROJECT_ROOT
        / "config"
        / "challenge_bank.json"
    )

    runner = ChallengeRunner(OUTPUT_FILE)

    run_episode(
        episode_id="EP-POLICY-NORMAL",
        config=MonitorConfig(
            monitor_id="policy-monitor",
            monitor_state=AgentState.NORMAL,
            behavior_mode=MonitorBehaviorMode.NORMAL,
        ),
        runner=runner,
        challenges=challenges,
    )

    run_episode(
        episode_id="EP-POLICY-COMPROMISED",
        config=MonitorConfig(
            monitor_id="policy-monitor",
            monitor_state=AgentState.COMPROMISED,
            behavior_mode=MonitorBehaviorMode.FALSE_ALLOW,
        ),
        runner=runner,
        challenges=challenges,
    )

    print(f"Challenge results written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
