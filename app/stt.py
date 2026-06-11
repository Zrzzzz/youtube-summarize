"""第 2 步：腾讯云「录音文件识别」把 mp3 转为文字。

录音文件识别本地上传单次限制 5MB，这里先用 ffmpeg 压成
16kHz 单声道 32kbps，再按 10 分钟切片（每片约 2.4MB），
逐片提交识别后拼接结果，因此不依赖 COS。
"""

import base64
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from tencentcloud.common import credential
from tencentcloud.asr.v20190614 import asr_client, models

from .config import settings

# 每个切片的时长（秒）。32kbps 下 600s ≈ 2.4MB，远低于 5MB 限制
_SEGMENT_SECONDS = 600
# 识别结果中的时间戳前缀，例如 "[0:1.640,0:3.480]  "
_TIMESTAMP_RE = re.compile(r"\[\d+:\d+(?:\.\d+)?,\d+:\d+(?:\.\d+)?\]\s*")


def _make_client() -> asr_client.AsrClient:
    if not settings.tencent_secret_id or not settings.tencent_secret_key:
        raise RuntimeError("缺少腾讯云密钥，请在 .env 中配置 TENCENT_SECRET_ID / TENCENT_SECRET_KEY")
    cred = credential.Credential(settings.tencent_secret_id, settings.tencent_secret_key)
    return asr_client.AsrClient(cred, settings.asr_region)


def _split_audio(mp3_path: Path, work_dir: Path) -> list[Path]:
    """压缩并切片，返回切片文件列表（按顺序）。"""
    pattern = work_dir / "seg_%04d.mp3"
    cmd = [
        "ffmpeg", "-y", "-i", str(mp3_path),
        "-ac", "1", "-ar", "16000", "-b:a", "32k",
        "-f", "segment", "-segment_time", str(_SEGMENT_SECONDS),
        str(pattern),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 切片失败: {proc.stderr[-2000:]}")
    segments = sorted(work_dir.glob("seg_*.mp3"))
    if not segments:
        raise RuntimeError("ffmpeg 没有产出任何音频切片")
    return segments


def _submit(client: asr_client.AsrClient, audio_bytes: bytes, engine: str) -> int:
    req = models.CreateRecTaskRequest()
    req.EngineModelType = engine
    req.ChannelNum = 1
    req.ResTextFormat = 0
    req.SourceType = 1  # 本地上传
    req.Data = base64.b64encode(audio_bytes).decode()
    req.DataLen = len(audio_bytes)
    resp = client.CreateRecTask(req)
    return resp.Data.TaskId


def _wait(client: asr_client.AsrClient, task_id: int, timeout: int = 1800, interval: int = 5) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        req = models.DescribeTaskStatusRequest()
        req.TaskId = task_id
        resp = client.DescribeTaskStatus(req)
        status = resp.Data.StatusStr  # waiting / doing / success / failed
        if status == "success":
            return resp.Data.Result or ""
        if status == "failed":
            raise RuntimeError(f"腾讯云识别失败 (TaskId={task_id}): {resp.Data.ErrorMsg}")
        time.sleep(interval)
    raise TimeoutError(f"腾讯云识别超时 (TaskId={task_id})")


def transcribe(mp3_path: Path, engine: str = "") -> str:
    """整段流程：切片 → 全部提交 → 依次等待 → 拼接纯文本。

    engine 为空时使用 settings.asr_engine_model。
    """
    engine = engine or settings.asr_engine_model
    client = _make_client()
    work_dir = Path(tempfile.mkdtemp(prefix="yts_stt_"))
    try:
        segments = _split_audio(mp3_path, work_dir)
        task_ids = [_submit(client, seg.read_bytes(), engine) for seg in segments]
        pieces = [_wait(client, tid) for tid in task_ids]
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    text = "\n".join(_TIMESTAMP_RE.sub("", p).strip() for p in pieces)
    text = text.strip()
    if not text:
        raise RuntimeError("识别结果为空，可能音频没有人声或语言与 ASR_ENGINE_MODEL 不匹配")
    return text
