
from src.database.models import (
    Base,
    engine,
    ComplaintEscalation,
    ManagerNotification,
)


def migrate():
    Base.metadata.create_all(bind=engine)

    print("Escalation and notification tables ready.")
    print("Existing complaint records preserved.")


if __name__ == "__main__":
    migrate()
