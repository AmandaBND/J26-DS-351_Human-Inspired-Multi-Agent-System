from emotion_aware_after_sales.database.setup_database import get_connection
from contextlib import closing, nullcontext


class ServiceAgent:
    """Retrieve repair requests and service-visit evidence."""

    name = "Service Agent"

    def analyze(self, customer_id: int, device_id: int, *, connection=None, unlimited=False):
        with (nullcontext(connection) if connection is not None else closing(get_connection())) as conn:
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
            "service_requests": [dict(row) for row in requests],
            "service_visits": [dict(row) for row in visits],
            "finding": (
                f"Found {len(requests)} service request(s) "
                f"and {len(visits)} recorded service visit(s)."
            ),
        }