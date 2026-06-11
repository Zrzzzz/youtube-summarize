"""第 4 步：通过 163 邮箱 SMTP 把总结发送出去。

需要在 163 邮箱网页版：设置 → POP3/SMTP/IMAP → 开启 SMTP 服务，
拿到「授权码」填入 .env 的 SMTP_PASS（不是登录密码）。
163 是国内服务，直连即可，不走代理。
"""

import smtplib
from email.message import EmailMessage

import markdown

from .config import settings


def is_configured() -> bool:
    return bool(settings.smtp_user and settings.smtp_pass)


def send_summary(recipient: str, title: str, summary_md: str) -> None:
    if not is_configured():
        raise RuntimeError("缺少邮箱配置，请在 .env 中设置 SMTP_USER / SMTP_PASS（163 授权码）")

    msg = EmailMessage()
    msg["Subject"] = f"[视频总结] {title}"
    msg["From"] = settings.smtp_user  # 163 要求发件人与登录账号一致
    msg["To"] = recipient
    msg.set_content(summary_md)  # 纯文本兜底
    msg.add_alternative(
        f"<html><body style='font-family:sans-serif;line-height:1.6'>"
        f"{markdown.markdown(summary_md)}</body></html>",
        subtype="html",
    )

    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=60) as smtp:
        smtp.login(settings.smtp_user, settings.smtp_pass)
        smtp.send_message(msg)
