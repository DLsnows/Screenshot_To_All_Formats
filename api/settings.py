from fastapi import APIRouter, Depends

from Screenshot_To_All_Formats.api.utils import get_settings_manager
from Screenshot_To_All_Formats.services.settings_manager import SettingsManager

router = APIRouter(tags=["settings"])


@router.get("/settings")
async def get_settings(
    sm: SettingsManager = Depends(get_settings_manager),
):
    """Return all current settings."""
    return sm.load()


@router.put("/settings")
async def put_settings(
    body: dict,
    sm: SettingsManager = Depends(get_settings_manager),
):
    """Update and persist settings."""
    sm.save(body)
    return sm.load()


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
