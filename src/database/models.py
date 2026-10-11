from datetime import datetime, timezone

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

engine = create_engine("sqlite:///data/complaints.db")

SessionLocal = sessionmaker(bind=engine)


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)

    customer_name = Column(String(150), nullable=False)

    product = Column(String(150), nullable=False)

    complaint_text = Column(Text, nullable=False)

    category = Column(String(100), nullable=True)

    emotion = Column(String(100), nullable=True)

    priority = Column(String(50), nullable=True)

    business_impact = Column(Text, nullable=True)

    recommended_resolution = Column(Text, nullable=True)

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
    print("Complaint database created successfully!")