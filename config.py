from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
DATABASE_URL: str = os.environ["DATABASE_URL"]
ADMIN_CHAT_ID: int = int(os.environ["ADMIN_CHAT_ID"])
