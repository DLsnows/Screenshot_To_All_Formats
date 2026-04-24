import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from PIL import ImageGrab

from Screenshot_To_All_Formats.api.utils import get_settings_manager
from Screenshot_To_All_Formats.services.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["clipboard"])


@router.post("/clipboard/capture")
async def capture_clipboard(
    sm: SettingsManager = Depends(get_settings_manager),
):
    """Capture an image from the system clipboard and save it to disk.

    Returns the directory and filename so the frontend can auto-fill the
    input path and optionally start a conversion.
    """
    cfg = sm.load()

    # Determine save directory
    save_dir = cfg.get("defaults", {}).get("input_path", "")
    if not save_dir:
        project_root = Path(__file__).resolve().parent.parent
        save_dir = str(project_root / "uploads")
    os.makedirs(save_dir, exist_ok=True)

    # Grab clipboard image
    try:
        clip = ImageGrab.grabclipboard()

        # None → clipboard has no image and no files
        if clip is None:
            return {"path": "", "filename": "", "error": "clipboard_empty"}

        # list → clipboard contains copied file references
        if isinstance(clip, list):
            img = None
            for fp in clip:
                ext = Path(fp).suffix.lower()
                if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"):
                    try:
                        from PIL import Image
                        img = Image.open(fp)
                        break
                    except Exception:
                        continue
            if img is None:
                return {"path": "", "filename": "", "error": "clipboard_empty"}

            # Use original filename stem for the saved copy
            stem = Path(clip[0]).stem if clip else "clipboard"

        else:
            # PIL Image directly
            img = clip
            stem = "clipboard"

    except Exception as exc:
        logger.error("Failed to grab clipboard image: %s", exc)
        return {"path": "", "filename": "", "error": str(exc)}

    # Save with timestamp
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{stem}_{ts}.png"
    filepath = os.path.join(save_dir, filename)
    img.save(filepath, "PNG")
    logger.info("Clipboard image saved: %s", filepath)

    return {"path": save_dir, "filename": filename, "error": ""}
