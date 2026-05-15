from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
DATABASE_URL: str = os.environ["DATABASE_URL"]
ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0") or "0")
ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0") or "0")
GOOGLE_SHEETS_SPREADSHEET_ID: str | None = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID") or None
GOOGLE_SERVICE_ACCOUNT_FILE: str | None = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or None
GOOGLE_SERVICE_ACCOUNT_JSON: str | None = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or None
