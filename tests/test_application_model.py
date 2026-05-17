import unittest

from database.models import Application


class ApplicationModelTest(unittest.TestCase):
    def test_driver_application_allows_missing_plate_number(self) -> None:
        plate_number = Application.__table__.c.plate_number

        self.assertTrue(plate_number.nullable)


if __name__ == "__main__":
    unittest.main()
