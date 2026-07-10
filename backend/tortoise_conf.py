import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_URL = os.getenv("DATABASE_URL", "local.db")
AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN") or None

def _is_remote_turso(url: str, token: str | None) -> bool:
    if not token:
        return False
    u = url.lower()
    if u.endswith(".db") or u.endswith(".sqlite") or u.endswith(".sqlite3"):
        return False
    if "turso.io" in u or "libsql://" in u:
        return True
    if token and len(token) > 20:
        return "turso" in u or "." in u and "/" not in u
    return False

IS_REMOTE = _is_remote_turso(RAW_URL, AUTH_TOKEN)

if IS_REMOTE:
    CLEAN_URL = RAW_URL.replace("libsql://", "").replace("https://", "").replace("http://", "").strip("/ ")
    TORTOISE_ORM = {
        "connections": {
            "default": {
                "engine": "backends.libsql",
                "credentials": {
                    "file_path": CLEAN_URL,
                    "auth_token": AUTH_TOKEN,
                },
            }
        },
        "apps": {
            "models": {
                "models": ["models", "aerich.models"],
                "default_connection": "default",
            },
        },
    }
    DATABASE_URL = CLEAN_URL
    TURSO_AUTH_TOKEN = AUTH_TOKEN
else:
    db_path = RAW_URL
    if not db_path or db_path == "local.db":
        base = Path(__file__).parent
        db_path = str(base / "local.db")
    if db_path.startswith("libsql://"):
        db_path = db_path.replace("libsql://", "")
    TORTOISE_ORM = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.sqlite",
                "credentials": {"file_path": db_path},
            }
        },
        "apps": {
            "models": {
                "models": ["models", "aerich.models"],
                "default_connection": "default",
            },
        },
    }
    DATABASE_URL = db_path
    TURSO_AUTH_TOKEN = None
