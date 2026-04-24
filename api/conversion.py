import os
import shutil
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from Screenshot_To_All_Formats.api.utils import (
    ConversionRequest,
    task_to_response,
    get_task_manager,
    get_settings_manager,
)
from Screenshot_To_All_Formats.services.task_manager import TaskManager, TaskStatus
from Screenshot_To_All_Formats.services.settings_manager import SettingsManager
from Screenshot_To_All_Formats.services.ocr_engine import process_all_images, IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversion"])


# ---------------------------------------------------------------------------
# Start a conversion task
# ---------------------------------------------------------------------------

@router.post("/convert")
async def start_conversion(
    req: ConversionRequest,
    tm: TaskManager = Depends(get_task_manager),
    sm: SettingsManager = Depends(get_settings_manager),
):
    """Start a new image-to-format conversion task.

    Returns immediately with a ``task_id`` that can be polled via
    ``GET /tasks/{task_id}``.
    """
    # Validate input path
    if not os.path.isdir(req.input_path):
        raise HTTPException(status_code=400, detail=f"Input path not found: {req.input_path}")

    # Count images upfront
    image_files = sorted(
        f for f in os.listdir(req.input_path)
        if Path(f).suffix.lower() in IMAGE_EXTENSIONS
    )
    if not image_files:
        raise HTTPException(status_code=400, detail="No supported image files found in input directory")

    # Create the task
    task_id = tm.create_task(
        input_path=req.input_path,
        output_path=req.output_path,
        language=req.language.value,
        format=req.format.value,
        copy_to_clipboard=req.copy_to_clipboard,
        model_config=req.model.model_dump(),
    )
    tm.set_total(task_id, len(image_files))
    tm.set_status(task_id, TaskStatus.RUNNING)

    # Launch background worker in a thread pool
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run_ocr_worker, task_id, req, tm, sm)

    return {"task_id": task_id, "total_images": len(image_files)}


# ---------------------------------------------------------------------------
# Poll task status
# ---------------------------------------------------------------------------

@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    tm: TaskManager = Depends(get_task_manager),
):
    """Return the current status of a conversion task."""
    task = tm.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_response(task)


# ---------------------------------------------------------------------------
# List recent tasks
# ---------------------------------------------------------------------------

@router.get("/tasks")
async def list_tasks(
    limit: int = 50,
    tm: TaskManager = Depends(get_task_manager),
):
    """Return recent tasks (newest first)."""
    tasks = tm.list_tasks(limit=limit)
    return [task_to_response(t) for t in tasks]


# ---------------------------------------------------------------------------
# Delete a task
# ---------------------------------------------------------------------------

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    tm: TaskManager = Depends(get_task_manager),
):
    """Remove a task from the in-memory store."""
    if not tm.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": task_id}


# ---------------------------------------------------------------------------
# Download combined result file
# ---------------------------------------------------------------------------

@router.get("/tasks/{task_id}/download")
async def download_result(
    task_id: str,
    tm: TaskManager = Depends(get_task_manager),
):
    """Download the ``all_in_one`` output file for a completed task."""
    task = tm.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Task is not yet completed")

    ext_map = {
        "markdown": ".md", "html": ".html", "csv": ".csv",
        "json": ".json", "latex": ".tex", "text": ".txt", "code": ".txt",
    }
    filename = f"all_in_one{ext_map.get(task.format, '.txt')}"
    filepath = os.path.join(task.output_path, filename)

    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Output file not found on disk")

    return FileResponse(filepath, filename=filename)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _run_ocr_worker(
    task_id: str,
    req: ConversionRequest,
    tm: TaskManager,
    sm: SettingsManager,
) -> None:
    """Run OCR in a background thread, updating task state as it goes."""
    try:
        # Create a subfolder to stash successfully processed images so they
        # don't get picked up by future conversions of the same directory.
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        processed_dir = os.path.join(req.input_path, f"_processed_{ts}")
        os.makedirs(processed_dir, exist_ok=True)

        def on_progress(completed: int, total: int):
            tm.update_progress(task_id, completed)

        def on_image_done(img_path: str):
            """Move a successfully processed image into the processed folder."""
            dest = os.path.join(processed_dir, os.path.basename(img_path))
            try:
                shutil.move(img_path, dest)
            except OSError:
                pass  # best-effort

        results, combined = process_all_images(
            input_path=req.input_path,
            output_path=req.output_path,
            language=req.language.value,
            format=req.format.value,
            model_config=req.model.model_dump(),
            progress_callback=on_progress,
            on_image_done=on_image_done,
        )

        tm.complete_task(task_id, results, combined)

        # Optionally copy the last result to clipboard
        if req.copy_to_clipboard and results:
            try:
                import pyperclip
                pyperclip.copy(results[-1])
            except Exception:
                logger.warning("Failed to copy to clipboard", exc_info=True)

    except Exception as exc:
        logger.error("OCR worker failed", exc_info=True)
        tm.fail_task(task_id, str(exc))
