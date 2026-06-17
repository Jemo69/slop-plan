import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".plan-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key() -> str | None:
    config = load_config()
    return config.get("api_key")


def get_api_url() -> str:
    config = load_config()
    return config.get("api_url", "http://localhost:8000")


def set_api_key(api_key: str) -> None:
    config = load_config()
    config["api_key"] = api_key
    save_config(config)


def set_api_url(api_url: str) -> None:
    config = load_config()
    config["api_url"] = api_url
    save_config(config)
