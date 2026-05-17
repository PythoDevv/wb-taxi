import os
import unittest
from datetime import datetime

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/test")

from database.reports import APPLICATION_HEADERS, ReportRow
from services.google_sheets import application_rows_to_values


class ReportVisibilityTest(unittest.TestCase):
    def test_application_exports_hide_plate_number(self) -> None:
        row = ReportRow(
            application_type="brand",
            application_id=1,
            telegram_id=123,
            username="tester",
            user_created_at=datetime(2026, 1, 1),
            full_name="Test User",
            phone="998901234567",
            promocode="PROMO",
            plate_number="01A123BC",
            status="new",
            created_at=datetime(2026, 1, 2),
            car_model="Cobalt",
            car_year="2020",
            car_color="White",
        )

        values = application_rows_to_values([row])
        flattened_values = [str(value) for value in values[1]]

        self.assertNotIn("plate_number", APPLICATION_HEADERS)
        self.assertNotIn("01A123BC", flattened_values)


if __name__ == "__main__":
    unittest.main()
