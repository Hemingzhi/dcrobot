from pathlib import Path

import yaml

_CONFIG_CACHE = None

def load_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        project_root = Path(__file__).resolve().parent.parent
        config_path = project_root / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"config.yaml not found at {config_path}")

        with config_path.open("r", encoding="utf-8") as f:
            _CONFIG_CACHE = yaml.safe_load(f)

    return _CONFIG_CACHE
