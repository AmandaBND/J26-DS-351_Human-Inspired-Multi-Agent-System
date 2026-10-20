
from datetime import date

from emotion_aware_after_sales.database.setup_database import get_connection


class AMCDecisionService:
    """Read AMC records and generate explainable prototype decisions."""

    def list_customers(self):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT customer_id, customer_name
                FROM customers
                ORDER BY customer_name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_customer_profile(self, customer_id, device_id):
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    c.customer_id,
                    c.customer_name,
                    c.phone_number,
                    c.email,
                    c.purchase_date,
                    c.warranty_start_date,
                    c.warranty_end_date,
                    d.device_id,
                    d.device_type,
                    d.brand,
                    d.model,
                    d.serial_number,
                    d.device_features,
                    d.warranty_period_months
                FROM customers c
                JOIN customer_devices cd
                    ON cd.customer_id = c.customer_id
                JOIN devices d
                    ON d.device_id = cd.device_id
                WHERE c.customer_id = ?
                   AND d.device_id = ?
                """,
                (customer_id,device_id),
            ).fetchone()

        return dict(row) if row else None

    def get_amc_contracts(self, customer_id, device_id):
        with get_connection() as conn:
            rows = conn.execute(
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

        return [dict(row) for row in rows]

    def get_service_history(self, customer_id, device_id):
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    service_date,
                    issue_description,
                    resolution,
                    service_status
                FROM service_history
                WHERE customer_id = ?
                  AND device_id = ?
                ORDER BY service_date DESC
                """,
                (customer_id, device_id),
            ).fetchall()

        return [dict(row) for row in rows]

    def recommend(self, profile, contracts, history):
        today = date.today()

        warranty_end = date.fromisoformat(
            profile["warranty_end_date"]
        )
        warranty_active = (
            date.fromisoformat(profile["warranty_start_date"])
            <= today <= warranty_end
        )

        unresolved = [
            item for item in history
            if str(item["service_status"]).strip().casefold()
            not in {"resolved", "closed", "completed"}
        ]

        actions = []
        reasons = []

        if unresolved:
            actions.append("Arrange service-team follow-up")
            reasons.append(
                f"{len(unresolved)} unresolved service issue(s)"
            )

        if warranty_active:
            actions.append("Verify warranty coverage before paid service")
            reasons.append("Device is currently within warranty dates")

        current_contract = next(
            (
                contract
                for contract in contracts
                if date.fromisoformat(contract["start_date"])
                <= today <= date.fromisoformat(contract["end_date"])
            ),
            None,
        )

        if current_contract:
            days_remaining = (
                date.fromisoformat(current_contract["end_date"])
                - today
            ).days

            if days_remaining <= 30:
                actions.append("Initiate AMC renewal follow-up")
                reasons.append(
                    f"AMC expires in {days_remaining} day(s)"
                )

            amc_status = "Active"

        elif contracts:
            latest = contracts[0]
            latest_start = date.fromisoformat(latest["start_date"])
            latest_end = date.fromisoformat(latest["end_date"])

            if latest_end < today:
                amc_status = "Expired"
                actions.append("Review AMC renewal eligibility")
                reasons.append("Latest AMC contract has expired")
            elif latest_start > today:
                amc_status = "Upcoming"
                reasons.append("AMC coverage has not started yet")
            else:
                amc_status = "Review required"
                reasons.append("AMC dates require manual review")

        else:
            amc_status = "No AMC contract"
            actions.append("Check AMC enrollment eligibility")
            reasons.append("No AMC contract exists for this device")

        if not actions:
            actions.append("Continue routine customer follow-up")
            reasons.append("No immediate service or renewal trigger")

        return {
            "amc_status": amc_status,
            "warranty_status": (
                "Under warranty" if warranty_active else "Out of warranty"
            ),
            "recommended_actions": actions,
            "decision_reasons": reasons,
        }
