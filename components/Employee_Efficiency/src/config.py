"""Central configuration. All paths/keys come from here."""
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
RAW_DIR = DATA_DIR / "raw"
TRUTH_DIR = DATA_DIR / "synthetic_truth"
PRIVATE_DIR = DATA_DIR / "private"
DB_PATH = Path(os.getenv("DATABASE_PATH", DATA_DIR / "employee_efficiency_company.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
USE_LLM = os.getenv("USE_LLM", "true").lower() == "true" and bool(OPENROUTER_API_KEY)

RANDOM_SEED = 42
BASELINE_YEAR = 2024          # historical year used to set benchmarks/targets
DATA_START = "2024-01"
DATA_END = "2026-09"          # last fully closed month in operational dataset
EXTRACT_DT = datetime(2026, 10, 2, 9, 0)
CONVERSION_WINDOW_DAYS = 45
REPEAT_WINDOW_DAYS = 14
MIN_N = {
    "technician": 8,
    "tpo_service": 30,
    "amc_processing": 8,
    "contracts_coordinator": 15,
}
MIN_CSAT_RESPONSES = 5
MIN_KPI_COVERAGE = 0.85
WORKLOAD_RECENT_MONTHS = 3
