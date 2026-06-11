"""第 1 步：把 YouTube 视频下载为 mp3。

优先用 yt-dlp（可选最佳音轨）；当 YouTube 风控拦截（机器人验证）时，
自动回退到 Piped 公共实例：由实例的服务器 IP 代理访问 YouTube，
拿到带音轨的流后用 ffmpeg 抽成 mp3。
"""

import re
import subprocess
import tempfile
from pathlib import Path

import requests
import yt_dlp

from .config import settings

_VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([0-9A-Za-z_-]{11})")
# PO Token provider（vendor 目录存在时启用），配合 cookies 提高 yt-dlp 通过率
_BGUTIL_SERVER = Path(__file__).resolve().parent.parent / "vendor/bgutil-ytdlp-pot-provider/server"


def _proxies() -> dict:
    if not settings.proxy:
        return {}
    return {"http": settings.proxy, "https": settings.proxy}


def _video_id(url: str) -> str:
    m = _VIDEO_ID_RE.search(url)
    if not m:
        raise ValueError(f"无法从链接解析视频 ID: {url}")
    return m.group(1)


def _download_with_ytdlp(url: str) -> tuple[Path, str]:
    out_dir = settings.download_dir
    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": {"deno": {}, "node": {}},
    }
    if settings.proxy:
        opts["proxy"] = settings.proxy
    if settings.ytdlp_cookies_file:
        opts["cookiefile"] = settings.ytdlp_cookies_file
    elif settings.ytdlp_cookies_browser:
        opts["cookiesfrombrowser"] = (settings.ytdlp_cookies_browser,)
    if _BGUTIL_SERVER.exists():
        opts["extractor_args"] = {
            "youtubepot-bgutilscript": {"server_home": [str(_BGUTIL_SERVER)]}
        }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    mp3_path = out_dir / f"{info['id']}.mp3"
    if not mp3_path.exists():
        raise FileNotFoundError(f"下载完成但找不到音频文件: {mp3_path}")
    return mp3_path, info.get("title") or info["id"]


def _download_with_piped(url: str) -> tuple[Path, str]:
    vid = _video_id(url)
    last_err: Exception | None = None
    for instance in settings.piped_instances:
        try:
            resp = requests.get(f"{instance}/streams/{vid}", proxies=_proxies(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            title = data.get("title") or vid

            # 优先纯音频流（按码率从高到低），没有就退到带音轨的渐进式视频流（如 itag 18）
            stream = next(
                iter(
                    sorted(
                        (s for s in data.get("audioStreams", []) if s.get("url")),
                        key=lambda s: s.get("bitrate") or 0,
                        reverse=True,
                    )
                ),
                None,
            ) or next(
                (s for s in data.get("videoStreams", []) if s.get("url") and not s.get("videoOnly")),
                None,
            )
            if stream is None:
                raise RuntimeError("实例没有返回可用的音频流")

            mp3_path = settings.download_dir / f"{vid}.mp3"
            with tempfile.NamedTemporaryFile(suffix=".media", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                with requests.get(
                    stream["url"], proxies=_proxies(), timeout=600, stream=True
                ) as media:
                    media.raise_for_status()
                    with open(tmp_path, "wb") as f:
                        for chunk in media.iter_content(1 << 16):
                            f.write(chunk)
                proc = subprocess.run(
                    ["ffmpeg", "-y", "-i", str(tmp_path), "-vn",
                     "-acodec", "libmp3lame", "-b:a", "128k", str(mp3_path)],
                    capture_output=True, text=True,
                )
                if proc.returncode != 0:
                    raise RuntimeError(f"ffmpeg 转码失败: {proc.stderr[-500:]}")
            finally:
                tmp_path.unlink(missing_ok=True)
            return mp3_path, title
        except Exception as exc:  # noqa: BLE001 - 换下一个实例继续试
            last_err = exc
    raise RuntimeError(f"所有 Piped 实例均失败，最后错误: {last_err}")


def download_audio(url: str) -> tuple[Path, str]:
    """下载音频，返回 (mp3 路径, 视频标题)。"""
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    try:
        return _download_with_ytdlp(url)
    except yt_dlp.utils.DownloadError as exc:
        try:
            return _download_with_piped(url)
        except Exception as piped_exc:
            raise RuntimeError(
                f"yt-dlp 与 Piped 回退均失败。yt-dlp: {exc}；Piped: {piped_exc}"
            ) from piped_exc
