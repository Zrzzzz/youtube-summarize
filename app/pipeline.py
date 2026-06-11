"""把四个步骤串成完整流水线。"""

from collections.abc import Callable

from . import downloader, mailer, stt, summarizer
from .config import settings

ProgressCallback = Callable[[str], None]


def _pick_engine(url: str, engine: str) -> str:
    """显式指定 > B 站默认中文 > 配置默认。"""
    if engine:
        return engine
    if downloader.is_bilibili(url):
        return "16k_zh"
    return settings.asr_engine_model


def run(
    url: str,
    recipient: str = "",
    on_progress: ProgressCallback | None = None,
    engine: str = "",
) -> dict:
    """执行完整流程，返回 {title, transcript, summary}。

    recipient 为空时跳过发邮件这一步。
    engine 为空时自动选择转写引擎（B 站中文，其余用配置默认）。
    on_progress 在每个阶段开始时收到阶段名：
    downloading / transcribing / summarizing / emailing
    """

    def progress(stage: str) -> None:
        if on_progress:
            on_progress(stage)

    progress("downloading")
    mp3_path, title = downloader.download_audio(url)

    progress("transcribing")
    transcript = stt.transcribe(mp3_path, engine=_pick_engine(url, engine))

    progress("summarizing")
    summary = summarizer.summarize(transcript, title)

    result = {"title": title, "transcript": transcript, "summary": summary}

    if recipient:
        progress("emailing")
        try:
            mailer.send_summary(recipient, title, summary)
        except Exception as exc:  # 邮件失败不应丢掉已经花钱算出来的总结
            result["email_error"] = str(exc)

    return result
