"""集中配置：全部从环境变量 / .env 读取。"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # 腾讯云 ASR
    tencent_secret_id: str = field(default_factory=lambda: os.getenv("TENCENT_SECRET_ID", ""))
    tencent_secret_key: str = field(default_factory=lambda: os.getenv("TENCENT_SECRET_KEY", ""))
    asr_region: str = field(default_factory=lambda: os.getenv("ASR_REGION", "ap-shanghai"))
    # 标准引擎走「录音文件识别」免费包：中文 16k_zh，英文 16k_en；
    # 16k_zh_large（大模型版，支持中英粤）是单独计费的 SKU，免费包不覆盖
    asr_engine_model: str = field(default_factory=lambda: os.getenv("ASR_ENGINE_MODEL", "16k_zh"))

    # DeepSeek
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    deepseek_model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    # 转写文本超过该字符数时截断，避免超出模型上下文
    max_transcript_chars: int = field(default_factory=lambda: int(os.getenv("MAX_TRANSCRIPT_CHARS", "80000")))

    # 163 邮箱 SMTP（SMTP_PASS 填授权码，在 163 设置里开启 SMTP 服务后获取）
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.163.com"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "465")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_pass: str = field(default_factory=lambda: os.getenv("SMTP_PASS", ""))
    default_recipient: str = field(default_factory=lambda: os.getenv("DEFAULT_RECIPIENT", ""))

    # 下载
    download_dir: Path = field(default_factory=lambda: Path(os.getenv("DOWNLOAD_DIR", "downloads")))
    # 代理只用于 YouTube 下载和 Gmail/Google；腾讯云与 DeepSeek 始终直连国内网络
    proxy: str = field(default_factory=lambda: os.getenv("PROXY", ""))
    # YouTube 触发机器人验证时需要登录 cookies，二选一：
    # 从本机浏览器读取（chrome / safari / edge / firefox）
    ytdlp_cookies_browser: str = field(default_factory=lambda: os.getenv("YTDLP_COOKIES_BROWSER", ""))
    # 或 Netscape 格式的 cookies.txt 文件路径
    ytdlp_cookies_file: str = field(default_factory=lambda: os.getenv("YTDLP_COOKIES_FILE", ""))
    # yt-dlp 被风控拦截时回退用的 Piped 公共实例，逗号分隔
    piped_instances: list = field(
        default_factory=lambda: [
            u.strip().rstrip("/")
            for u in os.getenv("PIPED_INSTANCES", "https://api.piped.private.coffee").split(",")
            if u.strip()
        ]
    )


settings = Settings()
