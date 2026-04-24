import os
import shutil
from datetime import datetime

from fastapi import APIRouter, UploadFile, File

router = APIRouter(tags=["upload"])


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """Upload one or more image files.

    Files are saved into a timestamped subdirectory under ``uploads/``.
    Returns the uploaded filenames and the directory path so it can be
    used as the ``input_path`` for a subsequent conversion request.
    """
    # Determine the project-relative uploads directory
    # (same location as config.json — parent of the api/ package)
    api_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(api_dir)
    base_upload_dir = os.path.join(project_root, "uploads")

    # Create a timestamped subdirectory for this batch
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = os.path.join(base_upload_dir, ts)
    os.makedirs(batch_dir, exist_ok=True)

    uploaded = []
    for f in files:
        if not f.filename:
            continue
        dest = os.path.join(batch_dir, os.path.basename(f.filename))
        with open(dest, "wb") as buf:
            shutil.copyfileobj(f.file, buf)
        uploaded.append(f.filename)

    return {
        "uploaded": uploaded,
        "upload_dir": batch_dir,
    }
