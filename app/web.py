"""第 5 步：FastAPI 网站，提交任务后在后台执行并可轮询进度。"""

import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import mailer, pipeline
from .config import settings

app = FastAPI(title="YouTube 视频总结")

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# 任务存在内存里，重启即丢失；单机自用够了
_tasks: dict[str, dict] = {}
_lock = threading.Lock()


class CreateTaskRequest(BaseModel):
    url: str = Field(..., description="YouTube 视频链接")
    email: str = Field("", description="收件邮箱，留空则用 DEFAULT_RECIPIENT；都为空则不发邮件")


def _run_task(task_id: str, url: str, recipient: str) -> None:
    def on_progress(stage: str) -> None:
        with _lock:
            _tasks[task_id]["stage"] = stage

    try:
        result = pipeline.run(url, recipient, on_progress)
        with _lock:
            _tasks[task_id].update(status="done", stage="done", **result)
    except Exception as exc:  # noqa: BLE001 - 后台线程里必须兜住一切异常
        with _lock:
            _tasks[task_id].update(status="failed", error=str(exc))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/api/mail/status")
def mail_status() -> dict:
    return {"configured": mailer.is_configured()}


@app.post("/api/tasks")
def create_task(req: CreateTaskRequest) -> dict:
    recipient = req.email.strip() or settings.default_recipient
    task_id = uuid.uuid4().hex[:12]
    with _lock:
        _tasks[task_id] = {
            "status": "running",
            "stage": "pending",
            "url": req.url,
            "email": recipient,
        }
    threading.Thread(target=_run_task, args=(task_id, req.url, recipient), daemon=True).start()
    return {"task_id": task_id}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    with _lock:
        task = _tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return dict(task)
