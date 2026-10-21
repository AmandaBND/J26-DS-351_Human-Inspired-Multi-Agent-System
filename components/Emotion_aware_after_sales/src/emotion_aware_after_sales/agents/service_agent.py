
from contextlib import closing, nullcontext

from emotion_aware_after_sales.database.setup_database import get_connection


class ServiceAgent:
    """Retrieve historical services, repair requests, and service visits."""

    name = "Service Agent"

    def analyze(self, customer_id: int, device_id: int, *, connection=None, unlimited=False):
        with (
            nullcontext(connection)
            if connection is not None
            else closing(get_connection())
        ) as conn:
            history = conn.execute(
                """
                SELECT
                    service_id,
                    customer_id,
                    device_id,
                    service_date,
                    issue_description,
                    resolution,
                    service_status
                FROM service_history
                WHERE customer_id = ?
                  AND device_id = ?
                ORDER BY service_date DESC
                LIMIT ?
                """,
                (customer_id, device_id, -1 if unlimited else 30),
            ).fetchall()

            requests = conn.execute(
                """
                SELECT
                    request_id,
                    request_number,
                    opened_at,
                    issue_description,
                    priority,
                    status
                FROM service_requests
                WHERE customer_id = ?
                  AND device_id = ?
                ORDER BY opened_at DESC
                LIMIT ?
                """,
                (customer_id, device_id, -1 if unlimited else 20),
            ).fetchall()

            visits = conn.execute(
                """
                SELECT
                    sv.visit_id,
                    sv.request_id,
                    sv.scheduled_at,
                    sv.completed_at,
                    sv.technician_name,
                    sv.resolution,
                    sr.status AS request_status
                FROM service_visits sv
                JOIN service_requests sr
                    ON sr.request_id = sv.request_id
                WHERE sr.customer_id = ?
                  AND sr.device_id = ?
                ORDER BY sv.scheduled_at DESC
                LIMIT ?
                """,
                (customer_id, device_id, -1 if unlimited else 30),
            ).fetchall()

        return {
            "agent": self.name,
            "status": "completed",
            "service_history": [dict(row) for row in history],
            "service_requests": [dict(row) for row in requests],
            "service_visits": [dict(row) for row in visits],
            "finding": (
                f"Found {len(history)} historical service record(s), "
                f"{len(requests)} service request(s), "
                f"and {len(visits)} recorded service visit(s)."
            ),
        }
