import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.environ["TELEGRAM_TOKEN"]
ALLOWED_USER_ID: int = int(os.environ["ALLOWED_USER_ID"])
DB_PATH: str = os.getenv("DB_PATH", "/data/vineyard.db")

# Ensure the data directory exists (guards against missing /data on Railway)
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
