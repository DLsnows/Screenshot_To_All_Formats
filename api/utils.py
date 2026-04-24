from enum import Enum
from typing import Any

from fastapi import Request
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Format(str, Enum):
    markdown = "markdown"
    html = "html"
    csv = "csv"
    json = "json"
    latex = "latex"
    text = "text"
    code = "code"


class Language(str, Enum):
    cn = "cn"
    en = "en"
    fr = "fr"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ModelConfig(BaseModel):
    model_config = {"protected_namespaces": ()}

    api_key: str
    base_url: str
    model_name: str
    max_tokens: int = Field(default=30000, ge=1024, le=200000)


class ConversionRequest(BaseModel):
    input_path: str
    output_path: str
    language: Language = Language.en
    format: Format = Format.markdown
    copy_to_clipboard: bool = False
    model: ModelConfig


class TaskStatusResponse(BaseModel):
    id: str
    status: str
    progress: int
    total: int
    percentage: int
    results: list[str] = []
    combined_result: str = ""
    error: str | None = None
    input_path: str = ""
    output_path: str = ""
    language: str = ""
    format: str = ""
    created_at: float = 0.0
    completed_at: float | None = None
    elapsed: float = 0.0


def task_to_response(task) -> TaskStatusResponse:
    """Convert a ConversionTask to a TaskStatusResponse."""
    return TaskStatusResponse(
        id=task.id,
        status=task.status.value,
        progress=task.progress,
        total=task.total,
        percentage=task.percentage,
        results=task.results,
        combined_result=task.combined_result,
        error=task.error,
        input_path=task.input_path,
        output_path=task.output_path,
        language=task.language,
        format=task.format,
        created_at=task.created_at,
        completed_at=task.completed_at,
        elapsed=task.elapsed,
    )


class SettingsResponse(BaseModel):
    defaults: dict[str, Any]
    model: dict[str, Any]
    ui: dict[str, Any]
    hotkey: dict[str, Any]


# ---------------------------------------------------------------------------
# FastAPI dependencies — pull singletons from app.state
# ---------------------------------------------------------------------------

def get_task_manager(request: Request):
    return request.app.state.task_manager


def get_settings_manager(request: Request):
    return request.app.state.settings_manager
