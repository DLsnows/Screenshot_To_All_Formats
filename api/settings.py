import logging
from fastapi import APIRouter, Depends, Request

from Screenshot_To_All_Formats.api.utils import get_settings_manager
from Screenshot_To_All_Formats.services.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])


@router.get("/settings")
async def get_settings(
    sm: SettingsManager = Depends(get_settings_manager),
):
    """Return all current settings."""
    return sm.load()


@router.put("/settings")
async def put_settings(
    request: Request,
    body: dict,
    sm: SettingsManager = Depends(get_settings_manager),
):
    """Update and persist settings, then sync the hotkey listener."""
    # Save the incoming settings
    sm.save(body)
    saved = sm.load()

    # Sync hotkey listener (start / stop / reload)
    _sync_hotkey(request, sm)

    return saved


@router.get("/languages")
async def get_languages():
    """Return supported content languages for OCR."""
    return SettingsManager.get_supported_content_languages()


@router.get("/ui-languages")
async def get_ui_languages():
    """Return supported UI languages."""
    return SettingsManager.get_supported_ui_languages()


@router.get("/formats")
async def get_formats():
    """Return supported output formats."""
    return SettingsManager.get_supported_formats()


@router.get("/hotkey/status")
async def hotkey_status(request: Request):
    """Return whether the global hotkey listener is currently active."""
    listener = getattr(request.app.state, "hotkey_listener", None)
    return {"running": listener is not None}


@router.get("/hotkey/events")
async def hotkey_events(since: str | None = None):
    """Return recent hotkey trigger events (polled by frontend for debugging)."""
    from Screenshot_To_All_Formats.hotkey.listener import get_recent_events
    return {"events": get_recent_events(since)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sync_hotkey(request: Request, sm: SettingsManager) -> None:
    """Start, stop, or reload the hotkey listener to match current settings."""
    cfg = sm.load()
    enabled = cfg.get("hotkey", {}).get("enabled", False)
    old_listener = getattr(request.app.state, "hotkey_listener", None)

    if enabled and old_listener is None:
        # Enable: start the listener
        try:
            from Screenshot_To_All_Formats.hotkey.listener import HotkeyListener  # noqa: F811
            tm = request.app.state.task_manager
            listener = HotkeyListener(tm, sm)
            listener.start()
            request.app.state.hotkey_listener = listener
            logger.info("Hotkey listener started via settings")
        except Exception as exc:
            logger.warning("Failed to start hotkey listener: %s", exc)

    elif enabled and old_listener is not None:
        # Already running: reload the combo (in case it changed)
        try:
            old_listener.reload()
        except Exception as exc:
            logger.warning("Failed to reload hotkey listener: %s", exc)

    elif not enabled and old_listener is not None:
        # Disable: stop the listener
        try:
            old_listener.stop()
        except Exception as exc:
            logger.warning("Failed to stop hotkey listener: %s", exc)
        request.app.state.hotkey_listener = None
