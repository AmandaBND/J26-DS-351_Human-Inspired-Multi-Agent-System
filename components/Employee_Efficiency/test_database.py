"""Print row counts for every table and KPI month coverage by role."""
from sqlalchemy import func, select

from src.database.models import Base, Employee, KPIRecord, SessionLocal, init_db

init_db()
with SessionLocal() as s:
    counts = {
        table.name: s.scalar(select(func.count()).select_from(table))
        for table in Base.metadata.sorted_tables
    }
    role_months = s.execute(
        select(Employee.role, func.count(func.distinct(KPIRecord.period)))
        .join(KPIRecord, Employee.id == KPIRecord.employee_id)
        .group_by(Employee.role)
        .order_by(Employee.role)
    ).all()
print("SQLite table rows:")
for table, count in counts.items():
    print(f"  {table:<24} {count:>8}")
print("KPI months by role:")
for role, months in role_months:
    print(f"  {role:<24} {months:>8}")
if counts.get("employees", 0) == 0:
    print("Empty. Load the company export with: uv run python -m src.services.preprocessing.pipeline")
else:
    print("Database OK")
