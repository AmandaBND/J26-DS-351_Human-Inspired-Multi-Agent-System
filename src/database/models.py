
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)


# ============================================================
# PROJECT PATH SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "complaints.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

engine = create_engine(
    f"sqlite:///{DATABASE_PATH.as_posix()}"
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


# ============================================================
# COMPLAINT DATABASE MODEL
# ============================================================

class Complaint(Base):

    __tablename__ = "complaints"

    # --------------------------------------------------------
    # BASIC COMPLAINT INFORMATION
    # --------------------------------------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    customer_name = Column(
        String(150),
        nullable=False,
    )

    product = Column(
        String(150),
        nullable=False,
    )

    complaint_text = Column(
        Text,
        nullable=False,
    )

    # --------------------------------------------------------
    # AGENT 1: COMPLAINT ANALYSIS
    # --------------------------------------------------------

    category = Column(String(100))
    issue_type = Column(String(200))
    summary = Column(Text)

    # --------------------------------------------------------
    # AGENT 2: CUSTOMER EMOTION ANALYSIS
    # --------------------------------------------------------

    emotion = Column(String(100))
    sentiment = Column(String(50))
    emotion_intensity = Column(String(50))
    emotion_score = Column(Integer)

    # --------------------------------------------------------
    # AGENT 3: PRIORITY AND BUSINESS IMPACT
    # --------------------------------------------------------

    priority = Column(String(50))
    priority_score = Column(Integer)
    proposed_sla_hours = Column(Integer)

    business_impact = Column(Text)

    # --------------------------------------------------------
    # AGENT 4: RESOLUTION RECOMMENDATION
    # --------------------------------------------------------

    recommended_resolution = Column(Text)
    resolution_details = Column(Text)
    customer_response = Column(Text)

    # --------------------------------------------------------
    # COMPLAINT PROCESSING STATUS
    # --------------------------------------------------------

    status = Column(
        String(50),
        default="Pending Analysis",
        nullable=False,
    )

    # --------------------------------------------------------
    # MANAGER APPROVAL / REJECTION INFORMATION
    # --------------------------------------------------------

    reviewed_by = Column(
        String(150),
        nullable=True,
    )

    review_comments = Column(
        Text,
        nullable=True,
    )

    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --------------------------------------------------------
    # COMPLAINT CREATION DATE
    # --------------------------------------------------------

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

def create_database():

    Base.metadata.create_all(bind=engine)


# ============================================================
# RUN DATABASE INITIALIZATION
# ============================================================

if __name__ == "__main__":

    create_database()

    print(
        "Complaint database initialized successfully!"
    )
