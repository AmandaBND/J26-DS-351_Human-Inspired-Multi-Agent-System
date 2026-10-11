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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "complaints.db"

engine = create_engine(
    f"sqlite:///{DATABASE_PATH.as_posix()}"
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


class Complaint(Base):
    __tablename__ = "complaints"

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

    category = Column(String(100))
    issue_type = Column(String(200))
    summary = Column(Text)

    emotion = Column(String(100))
    sentiment = Column(String(50))
    emotion_intensity = Column(String(50))
    emotion_score = Column(Integer)

    priority = Column(String(50))
    priority_score = Column(Integer)
    proposed_sla_hours = Column(Integer)

    business_impact = Column(Text)

    recommended_resolution = Column(Text)
    resolution_details = Column(Text)
    customer_response = Column(Text)

    status = Column(
        String(50),
        default="Pending Analysis",
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def create_database():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_database()
    print("Complaint database initialized successfully!")