import uuid
import time
import threading
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ConversionTask:
    """Represents a single image-to-format conversion task."""

    def __init__(
        self,
        task_id: str,
        input_path: str,
        output_path: str,
        language: str,
        format: str,
        copy_to_clipboard: bool,
        model_config: dict,
    ):
        self.id = task_id
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.total = 0
        self.results: list[str] = []
        self.combined_result: str = ""
        self.error: str | None = None
        self.input_path = input_path
        self.output_path = output_path
        self.language = language
        self.format = format
        self.copy_to_clipboard = copy_to_clipboard
        self.model_config = model_config
        self.created_at = time.time()
        self.completed_at: float | None = None
        self._seq = 0  # assigned by TaskManager.create_task for ordering

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict for API responses."""
        return {
            "id": self.id,
            "status": self.status.value,
            "progress": self.progress,
            "total": self.total,
            "results": self.results,
            "combined_result": self.combined_result,
            "error": self.error,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "language": self.language,
            "format": self.format,
            "copy_to_clipboard": self.copy_to_clipboard,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @property
    def elapsed(self) -> float:
        """Seconds elapsed since creation (or until completion)."""
        end = self.completed_at if self.completed_at else time.time()
        return end - self.created_at

    @property
    def percentage(self) -> int:
        """Progress as a 0-100 integer."""
        if self.total == 0:
            return 0
        return int(self.progress * 100 / self.total)


class TaskManager:
    """Thread-safe in-memory task storage.

    Tasks live in a dict guarded by a Lock.  Completed tasks are
    automatically evicted after ``max_age_hours`` (default 24).
    """

    def __init__(self, max_age_hours: int = 24):
        self._tasks: dict[str, ConversionTask] = {}
        self._lock = threading.Lock()
        self._max_age_hours = max_age_hours
        self._seq = 0  # monotonic counter for deterministic ordering

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_task(
        self,
        input_path: str,
        output_path: str,
        language: str,
        format: str,
        copy_to_clipboard: bool = False,
        model_config: dict | None = None,
    ) -> str:
        """Create a new task and return its UUID."""
        task_id = str(uuid.uuid4())
        task = ConversionTask(
            task_id=task_id,
            input_path=input_path,
            output_path=output_path,
            language=language,
            format=format,
            copy_to_clipboard=copy_to_clipboard,
            model_config=model_config or {},
        )
        with self._lock:
            task._seq = self._seq  # capture sequence under lock
            self._seq += 1
            self._tasks[task_id] = task
        return task_id

    def get_task(self, task_id: str) -> ConversionTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> list[ConversionTask]:
        """Return tasks newest-first, optionally capped."""
        with self._lock:
            sorted_tasks = sorted(
                self._tasks.values(),
                key=lambda t: (t.created_at, t._seq),
                reverse=True,
            )
            return sorted_tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def set_total(self, task_id: str, total: int) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.total = total

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = status

    def update_progress(self, task_id: str, progress: int) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.progress = progress

    def complete_task(
        self,
        task_id: str,
        results: list[str],
        combined_result: str,
    ) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED
                task.results = results
                task.combined_result = combined_result
                task.progress = task.total
                task.completed_at = time.time()

    def fail_task(self, task_id: str, error: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.ERROR
                task.error = error
                task.completed_at = time.time()

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.CANCELLED
                task.completed_at = time.time()
                return True
            return False

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def cleanup_old_tasks(self) -> int:
        """Remove tasks completed more than ``max_age_hours`` ago.

        Returns the number of removed tasks.
        """
        now = time.time()
        cutoff = now - self._max_age_hours * 3600
        with self._lock:
            to_delete = [
                tid
                for tid, t in self._tasks.items()
                if t.completed_at is not None and t.completed_at < cutoff
            ]
            for tid in to_delete:
                del self._tasks[tid]
        return len(to_delete)
