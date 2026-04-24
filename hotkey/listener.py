import os
import shutil
import time
import logging
import threading
from datetime import datetime

from pynput import keyboard
from PIL import ImageGrab

from Screenshot_To_All_Formats.services.ocr_engine import process_all_images
from Screenshot_To_All_Formats.services.task_manager import TaskManager, TaskStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hotkey event log (polled by frontend for debugging)
# ---------------------------------------------------------------------------

_hotkey_events: list[dict] = []
_hotkey_events_lock = threading.Lock()


def _add_hotkey_event(message: str) -> None:
    """Record a hotkey event for frontend polling."""
    with _hotkey_events_lock:
        _hotkey_events.append({
            "time": datetime.now().isoformat(),
            "message": message,
        })
        if len(_hotkey_events) > 20:
            _hotkey_events[:] = _hotkey_events[-20:]


def get_recent_events(since: str | None = None) -> list[dict]:
    """Return events after *since* timestamp (ISO format)."""
    with _hotkey_events_lock:
        if not since:
            return list(_hotkey_events)
        return [e for e in _hotkey_events if e["time"] > since]


# ---------------------------------------------------------------------------
# Normalised key identifiers (lowecase, no decoration)
# ---------------------------------------------------------------------------

_MODIFIER_MAP: dict[str, set] = {
    "ctrl": {"ctrl", "ctrl_l", "ctrl_r"},
    "alt": {"alt", "alt_l", "alt_r"},
    "shift": {"shift", "shift_l", "shift_r"},
    "win": {"cmd", "cmd_l", "cmd_r", "win", "win_l", "win_r"},
}


def _normalise(key):
    """Return a lower-case string identifier for a pynput key object."""
    if isinstance(key, keyboard.KeyCode):
        c = key.char
        return c.lower() if c else f"vk_{key.vk}"
    try:
        return key.name.lower()
    except AttributeError:
        return str(key)


def _to_canonical(key_name: str) -> str:
    """Map a raw key name (e.g. 'ctrl_l', 'shift_r') to its canonical form
    (e.g. 'ctrl', 'shift') using _MODIFIER_MAP.  Non-modifier keys pass
    through unchanged."""
    for canon, aliases in _MODIFIER_MAP.items():
        if key_name in aliases:
            return canon
    return key_name


# ---------------------------------------------------------------------------
# Hotkey listener
# ---------------------------------------------------------------------------

class HotkeyListener:
    """Listens for a user-configurable global hotkey.

    When triggered:
    1. Saves the clipboard image to the configured input directory.
    2. Starts an OCR conversion task with the current default settings.
    """

    def __init__(self, task_manager: TaskManager, settings_manager):
        self._tm = task_manager
        self._sm = settings_manager
        self._listener: keyboard.Listener | None = None
        self._pressed: set[str] = set()
        self._lock = threading.Lock()
        self._last_trigger = 0.0
        self._cooldown = 2.0  # seconds
        self._busy = False
        self._busy_lock = threading.Lock()

        # Parse initial combo from settings
        self._mods: set[str] = set()
        self._main_key: str | None = None
        self._reparse_combo()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        self._reparse_combo()
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        logger.info(
            "Hotkey listener started (combo=%s)", self._combo_str()
        )

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
            logger.info("Hotkey listener stopped")

    def reload(self):
        """Re-read the hotkey combo from settings (called after settings save)."""
        self._reparse_combo()

    # ------------------------------------------------------------------
    # Combo parsing
    # ------------------------------------------------------------------

    def _combo_str(self) -> str:
        parts = sorted(self._mods) + ([self._main_key] if self._main_key else [])
        return "+".join(parts)

    def _reparse_combo(self):
        raw = self._sm.get_hotkey_config().get("combo", "ctrl+shift+v")
        parts = [p.strip().lower() for p in raw.split("+") if p.strip()]

        mods: set[str] = set()
        main: str | None = None

        for p in parts:
            matched = False
            for mod_name, aliases in _MODIFIER_MAP.items():
                if p in aliases or p == mod_name:
                    mods.add(mod_name)
                    matched = True
                    break
            if not matched:
                main = p  # last non-modifier wins

        self._mods = mods
        self._main_key = main or "v"

    # ------------------------------------------------------------------
    # Key handlers
    # ------------------------------------------------------------------

    def _on_press(self, key):
        nk = _normalise(key)
        nk = _to_canonical(nk)
        with self._lock:
            self._pressed.add(nk)
            self._try_trigger()

    def _on_release(self, key):
        nk = _normalise(key)
        nk = _to_canonical(nk)
        with self._lock:
            self._pressed.discard(nk)

    def _try_trigger(self):
        # Debounce
        now = time.time()
        if now - self._last_trigger < self._cooldown:
            return

        # Check main key
        if self._main_key and self._main_key not in self._pressed:
            return

        # Check modifiers (all must be pressed, no extras)
        if not self._mods.issubset(self._pressed):
            return

        self._last_trigger = now
        threading.Thread(target=self._execute, daemon=True).start()

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def _execute(self):
        """Grab clipboard image, save it, and start a conversion task."""
        with self._busy_lock:
            if self._busy:
                logger.info("Hotkey ignored: conversion already in progress")
                return
            # Also check for any running tasks started from other sources
            for t in self._tm.list_tasks(limit=50):
                if t.status == TaskStatus.RUNNING:
                    logger.info("Hotkey ignored: another task is already running")
                    return
            self._busy = True

        _add_hotkey_event("Hotkey triggered, grabbing clipboard...")
        task_id = None

        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                _add_hotkey_event("Clipboard contains no image")
                logger.info("Hotkey triggered but clipboard contains no image")
                return

            cfg = self._sm.load()

            # Determine save directory
            save_dir = cfg.get("defaults", {}).get("input_path", "")
            if not save_dir:
                project_root = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                save_dir = os.path.join(project_root, "uploads")
            os.makedirs(save_dir, exist_ok=True)

            # Save image
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hotkey_{ts}.png"
            filepath = os.path.join(save_dir, filename)
            img.save(filepath, "PNG")
            logger.info("Clipboard image saved: %s", filepath)
            _add_hotkey_event(f"Clipboard image saved: {filename}")

            # Determine output directory
            out_dir = cfg.get("defaults", {}).get("output_path", "")
            if not out_dir:
                project_root = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                out_dir = os.path.join(project_root, "outputs")
            os.makedirs(out_dir, exist_ok=True)

            # Read current defaults
            language = cfg.get("defaults", {}).get("language", "en")
            fmt = cfg.get("ui", {}).get("format", "markdown")
            copy_clip = cfg.get("ui", {}).get("copy_to_clipboard", True)
            model_cfg = cfg.get("model", {})

            # Create task
            task_id = self._tm.create_task(
                input_path=save_dir,
                output_path=out_dir,
                language=language,
                format=fmt,
                copy_to_clipboard=copy_clip,
                model_config=model_cfg,
            )

            # Count images
            from pathlib import Path
            from Screenshot_To_All_Formats.services.ocr_engine import IMAGE_EXTENSIONS
            image_files = [
                f for f in os.listdir(save_dir)
                if Path(f).suffix.lower() in IMAGE_EXTENSIONS
            ]
            self._tm.set_total(task_id, len(image_files))
            self._tm.set_status(task_id, TaskStatus.RUNNING)

            # Create processed subfolder so already-processed images are
            # excluded from future hotkey conversions.
            ts_proc = datetime.now().strftime("%Y%m%d_%H%M%S")
            processed_dir = os.path.join(save_dir, f"_processed_{ts_proc}")
            os.makedirs(processed_dir, exist_ok=True)

            # Run OCR
            def on_progress(completed, total):
                self._tm.update_progress(task_id, completed)

            def on_image_done(img_path):
                dest = os.path.join(processed_dir, os.path.basename(img_path))
                try:
                    shutil.move(img_path, dest)
                except OSError:
                    pass

            results, combined = process_all_images(
                input_path=save_dir,
                output_path=out_dir,
                language=language,
                format=fmt,
                model_config=model_cfg,
                progress_callback=on_progress,
                on_image_done=on_image_done,
            )
            self._tm.complete_task(task_id, results, combined)

            # Copy last result to clipboard if configured
            if copy_clip and results:
                try:
                    import pyperclip
                    pyperclip.copy(results[-1])
                except Exception:
                    logger.warning("Failed to copy to clipboard", exc_info=True)

            logger.info(
                "Hotkey task %s completed: %d images → %s",
                task_id, len(results), fmt,
            )

        except Exception as exc:
            logger.error("Hotkey conversion failed: %s", exc, exc_info=True)
            if task_id:
                try:
                    self._tm.fail_task(task_id, str(exc))
                except Exception:
                    pass
        finally:
            with self._busy_lock:
                self._busy = False
