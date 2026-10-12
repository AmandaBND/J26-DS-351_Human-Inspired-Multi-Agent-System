from sqlalchemy import inspect, text

from src.database.models import engine


NEW_COLUMNS = {
    "sla_due_at": "DATETIME",
    "sla_completed_at": "DATETIME",
    "escalation_status": (
        "VARCHAR(50) NOT NULL DEFAULT 'Not Escalated'"
    ),
}


def migrate():
    inspector = inspect(engine)

    existing = {
        column["name"]
        for column in inspector.get_columns("complaints")
    }

    with engine.begin() as connection:
        for name, column_type in NEW_COLUMNS.items():
            if name not in existing:
                connection.execute(
                    text(
                        f"ALTER TABLE complaints "
                        f"ADD COLUMN {name} {column_type}"
                    )
                )
                print(f"Added column: {name}")
            else:
                print(f"Already exists: {name}")

    print("\nSLA database migration completed!")


if __name__ == "__main__":
    migrate()