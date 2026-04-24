import json
import os
import sys
from pathlib import Path
from threading import Lock

_DEFAULT_SETTINGS = {
    "defaults": {
        "input_path": "",
        "output_path": "",
        "language": "en"
    },
    "model": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model_name": "gpt-4o",
        "max_tokens": 30000
    },
    "ui": {
        "language": "en",
        "format": "markdown",
        "copy_to_clipboard": True
    },
    "hotkey": {
        "enabled": False,
        "combo": "ctrl+shift+v",
        "auto_start": True
    }
}

_SUPPORTED_CONTENT_LANGUAGES = ["cn", "en", "fr"]
_SUPPORTED_UI_LANGUAGES = ["en", "zh"]
_SUPPORTED_FORMATS = ["markdown", "html", "csv", "json", "latex", "text", "code"]


class SettingsManager:
    """Manages user settings persisted in config.json."""

    def __init__(self, config_path: str | None = None):
        if config_path:
            self.config_path = Path(config_path)
        elif getattr(sys, "frozen", False):
            # PyInstaller frozen — place config.json alongside the .exe
            self.config_path = Path(sys.executable).parent / "config.json"
        else:
            project_root = Path(__file__).resolve().parent.parent
            self.config_path = project_root / "config.json"
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> dict:
        """Load settings from config.json, falling back to defaults."""
        with self._lock:
            if not self.config_path.exists():
                return _deep_copy(_DEFAULT_SETTINGS)
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return _merge_with_defaults(data)
            except (json.JSONDecodeError, OSError):
                return _deep_copy(_DEFAULT_SETTINGS)

    def save(self, settings: dict) -> None:
        """Validate and persist settings to config.json."""
        validated = _merge_with_defaults(settings)
        with self._lock:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(validated, f, indent=2, ensure_ascii=False)

    def ensure_dirs(self) -> None:
        """Create uploads/ and outputs/ directories if missing."""
        project_root = self.config_path.parent
        for d in ("uploads", "outputs"):
            (project_root / d).mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def get_default_input_path(self) -> str:
        return self.load().get("defaults", {}).get("input_path", "")

    def get_default_output_path(self) -> str:
        return self.load().get("defaults", {}).get("output_path", "")

    def get_model_config(self) -> dict:
        return _deep_copy(self.load().get("model", _DEFAULT_SETTINGS["model"]))

    def get_ui_config(self) -> dict:
        return _deep_copy(self.load().get("ui", _DEFAULT_SETTINGS["ui"]))

    def get_hotkey_config(self) -> dict:
        return _deep_copy(self.load().get("hotkey", _DEFAULT_SETTINGS["hotkey"]))

    @staticmethod
    def get_supported_content_languages() -> list[str]:
        return list(_SUPPORTED_CONTENT_LANGUAGES)

    @staticmethod
    def get_supported_ui_languages() -> list[str]:
        return list(_SUPPORTED_UI_LANGUAGES)

    @staticmethod
    def get_supported_formats() -> list[str]:
        return list(_SUPPORTED_FORMATS)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _deep_copy(d: dict) -> dict:
    """Fast deep-copy for JSON-serialisable dicts."""
    return json.loads(json.dumps(d))


def _merge_with_defaults(data: dict) -> dict:
    """Merge user data over defaults so missing keys always have fallbacks."""
    result = _deep_copy(_DEFAULT_SETTINGS)

    for section in ("defaults", "model", "ui", "hotkey"):
        if section in data and isinstance(data[section], dict):
            result[section].update(
                (k, v) for k, v in data[section].items() if v is not None
            )

    # Sanity clamp
    model = result["model"]
    model["max_tokens"] = max(1024, min(model.get("max_tokens", 30000), 200000))

    defaults = result["defaults"]
    if defaults.get("language") not in _SUPPORTED_CONTENT_LANGUAGES:
        defaults["language"] = _DEFAULT_SETTINGS["defaults"]["language"]

    ui = result["ui"]
    if ui.get("language") not in _SUPPORTED_UI_LANGUAGES:
        ui["language"] = _DEFAULT_SETTINGS["ui"]["language"]
    if ui.get("format") not in _SUPPORTED_FORMATS:
        ui["format"] = _DEFAULT_SETTINGS["ui"]["format"]

    return result
