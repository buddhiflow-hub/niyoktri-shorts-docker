import os
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_storage_dir() -> Path:
    storage_env = os.getenv("STORAGE_DIR")
    if storage_env:
        path = Path(storage_env)
    else:
        path = get_base_dir() / "storage"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_config(config_path: Path = None) -> Dict[str, Any]:
    if config_path is None:
        # Check standard locations
        candidates = [
            Path("/app/config.yaml"),
            get_base_dir() / "config.yaml",
            Path("config.yaml"),
        ]
        for c in candidates:
            if c.exists():
                config_path = c
                break

    if not config_path or not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config
