from sqlalchemy import inspect, text

from src.database.models import engine


NEW_COLUMNS = {
    "reviewed_by": "VARCHAR(150)",
    "review_comments": "TEXT",
    "reviewed_at": "DATETIME",
}


def migrate():

    inspector = inspect(engine)

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("complaints")
    }

    with engine.begin() as connection:

        for name, column_type in NEW_COLUMNS.items():

            if name not in existing_columns:

                connection.execute(
                    text(
                        f"ALTER TABLE complaints "
                        f"ADD COLUMN {name} {column_type}"
                    )
                )

                print(f"Added column: {name}")

            else:
                print(f"Column already exists: {name}")

    print("\nDatabase migration completed!")


if __name__ == "__main__":
    migrate()