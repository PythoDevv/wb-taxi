import asyncio
import os
import unittest

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/test")

from services import google_sheets


class GoogleSheetsSyncTaskTest(unittest.TestCase):
    def test_periodic_sync_waits_then_runs_sync(self) -> None:
        calls: list[tuple[str, int | None]] = []

        async def fake_sleep(seconds: int) -> None:
            calls.append(("sleep", seconds))

        async def fake_sync() -> google_sheets.SheetsSyncResult:
            calls.append(("sync", None))
            raise asyncio.CancelledError

        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(
                google_sheets.run_periodic_google_sheets_sync(
                    interval_seconds=7,
                    sync_func=fake_sync,
                    sleep_func=fake_sleep,
                )
            )

        self.assertEqual(calls, [("sleep", 7), ("sync", None)])

    def test_schedule_google_sheets_sync_runs_in_background(self) -> None:
        async def run_test() -> None:
            calls: list[str] = []

            async def fake_sync() -> google_sheets.SheetsSyncResult:
                calls.append("sync")
                return google_sheets.SheetsSyncResult(
                    ok=True,
                    message="ok",
                    worksheet_count=1,
                )

            task = google_sheets.schedule_google_sheets_sync(
                reason="test",
                sync_func=fake_sync,
            )
            self.assertIsNotNone(task)
            await task

            self.assertEqual(calls, ["sync"])

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
