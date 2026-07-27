"""Persistent config for SDForest Contribution Tool.

Stored at ~/.sdforest-companion/config.json
"""
import json
import pathlib

_CONFIG_DIR = pathlib.Path.home() / ".sdforest-companion"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

_DEFAULTS = {
    "llamaparse_api_key": "",
    "gateway_url": "https://chloe.blumenkraft.cloud/contrib",
    "last_target_os": "hypertrophy",
}


def load_config() -> dict:
    """Return persisted config merged with defaults (so new keys are always present)."""
    cfg = dict(_DEFAULTS)
    if _CONFIG_FILE.exists():
        try:
            on_disk = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            cfg.update(on_disk)
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> None:
    """Persist config to disk, creating the directory if needed."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
