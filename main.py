import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Ensure the project root is on sys.path (so the package can be found
# even when running `python main.py` from inside the package directory).
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ---------------------------------------------------------------------------
# Trigger prompt registration — must happen before any OCR call
# ---------------------------------------------------------------------------
import Screenshot_To_All_Formats.prompt_setting as prompt_setting  # noqa: F401

from Screenshot_To_All_Formats.api.router import api_router
from Screenshot_To_All_Formats.services.task_manager import TaskManager
from Screenshot_To_All_Formats.services.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons (also referenced by hotkey listener)
# ---------------------------------------------------------------------------
task_manager = TaskManager()
settings_manager = SettingsManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # ---- startup ----
    settings_manager.ensure_dirs()
    app.state.task_manager = task_manager
    app.state.settings_manager = settings_manager

    # Conditionally start hotkey listener
    hotkey_listener = None
    try:
        cfg = settings_manager.load()
        if cfg.get("hotkey", {}).get("enabled", False):
            from Screenshot_To_All_Formats.hotkey.listener import HotkeyListener  # noqa: F811
            hotkey_listener = HotkeyListener(task_manager, settings_manager)
            hotkey_listener.start()
            app.state.hotkey_listener = hotkey_listener
            logger.info("Hotkey listener started")
    except Exception as exc:
        logger.warning("Failed to start hotkey listener: %s", exc)

    yield

    # ---- shutdown ----
    if hotkey_listener:
        hotkey_listener.stop()
        logger.info("Hotkey listener stopped")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Screenshot to Format Converter",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api")

# Mount static files (served at /static/...)
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import threading
    import time
    import webbrowser

    import socket

    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))

    # Auto-detect available port if the configured one is in use
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                break  # port is free
            except OSError:
                port += 1  # try next port

    frontend_url = f"http://{host}:{port}/static/index.html"

    # Open browser shortly after server starts
    def _open_browser():
        time.sleep(1.5)
        try:
            webbrowser.open(frontend_url)
        except Exception:
            pass

    threading.Thread(target=_open_browser, daemon=True).start()

    print(f"Starting Screenshot to Format Converter on http://{host}:{port}")
    print(f"API docs at http://{host}:{port}/docs")
    print(f"Frontend at {frontend_url}")
    print()

    uvicorn.run(
        "Screenshot_To_All_Formats.main:app",
        host=host,
        port=port,
        reload=True,
    )
