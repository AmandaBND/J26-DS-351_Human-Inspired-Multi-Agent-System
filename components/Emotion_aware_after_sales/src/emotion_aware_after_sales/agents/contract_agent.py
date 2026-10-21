from contextlib import closing, nullcontext
from emotion_aware_after_sales.database.setup_database import get_connection


class ContractAgent:
    """Retrieve verified customer, device, and AMC contract facts."""

    name = "Contract Agent"

    def analyze(self, customer_id: int, device_id: int, *, connection=None):
        with (nullcontext(connection) if connection is not None else closing(get_connection())) as conn:
            ownership = conn.execute(
                """
                SELECT
                    c.customer_id,
                    c.customer_name,
                    d.device_id,
                    d.device_type,
                    d.brand,
                    d.model,
                    cd.warranty_end_date
                FROM customer_devices cd
                JOIN customers c
                    ON c.customer_id = cd.customer_id
                JOIN devices d
                    ON d.device_id = cd.device_id
                WHERE cd.customer_id = ?
                  AND cd.device_id = ?
                """,
                (customer_id, device_id),
            ).fetchone()

            if ownership is None:
                return {
                    "agent": self.name,
                    "status": "not_found",
                    "finding": "The device is not registered to this customer.",
                    "contracts": [],
                }

            contracts = conn.execute(
                """
                SELECT
                    contract_id,
                    start_date,
                    end_date,
                    contract_status,
                    coverage_type
                FROM amc_contracts
                WHERE customer_id = ?
                  AND device_id = ?
                ORDER BY end_date DESC
                """,
                (customer_id, device_id),
            ).fetchall()

        return {
            "agent": self.name,
            "status": "completed",
            "customer": dict(ownership),
            "contracts": [dict(row) for row in contracts],
            "finding": (
                f"Verified customer-device ownership. "
                f"Found {len(contracts)} AMC contract(s)."
            ),
        }