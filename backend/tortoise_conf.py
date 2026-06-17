import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "local.db")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", None)

TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "backends.libsql",
            "credentials": {
                "file_path": DATABASE_URL,
                "auth_token": TURSO_AUTH_TOKEN,
            },
        }
    },
    "apps": {
        "models": {
            "models": ["models"],
            "default_connection": "default",
        },
    },
}
