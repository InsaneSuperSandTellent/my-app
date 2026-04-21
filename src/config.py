import os
from dotenv import load_dotenv

load_dotenv(".env.local")

def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value

ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")
SNIPEIT_URL: str = _require("SNIPEIT_URL")
SNIPEIT_API_KEY: str = _require("SNIPEIT_API_KEY")
INVOICES_FOLDER: str = _require("INVOICES_FOLDER")
LOG_FILE: str = _require("LOG_FILE")
