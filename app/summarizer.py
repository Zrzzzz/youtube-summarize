"""第 3 步：调用 DeepSeek（OpenAI 兼容接口）总结转写文本。"""

from openai import OpenAI

from .config import settings

_SYSTEM_PROMPT = """\
你是一个专业的视频内容总结助手。用户会给你一段视频的语音转写文本（可能含少量识别错误，请自行纠正理解）。
请用简体中文输出 Markdown 格式的总结，包含：

## 一句话概括
## 核心内容
（按主题分点，保留关键数据、结论与论据）
## 金句 / 值得注意的细节
（如果有）

总结要忠于原文，不要编造内容。"""


def summarize(transcript: str, title: str) -> str:
    if not settings.deepseek_api_key:
        raise RuntimeError("缺少 DeepSeek 密钥，请在 .env 中配置 DEEPSEEK_API_KEY")

    if len(transcript) > settings.max_transcript_chars:
        transcript = transcript[: settings.max_transcript_chars] + "\n\n（转写文本过长，已截断）"

    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    resp = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"视频标题：{title}\n\n转写文本：\n{transcript}"},
        ],
        temperature=0.6,
    )
    summary = resp.choices[0].message.content
    if not summary:
        raise RuntimeError("DeepSeek 返回了空内容")
    return summary
