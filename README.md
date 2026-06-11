# youtube-summarize

输入 YouTube 链接，自动完成：**下载音频 (yt-dlp) → 腾讯云语音转写 → DeepSeek 总结 → 邮件发送（163 SMTP）**，并提供网页调用。

## 准备

1. 安装 [ffmpeg](https://ffmpeg.org)（macOS: `brew install ffmpeg`）和 [uv](https://docs.astral.sh/uv/)
2. 复制配置并填好密钥：

```bash
cp .env.example .env
```

需要的凭证：

| 配置项 | 来源 |
| --- | --- |
| `TENCENT_SECRET_ID` / `TENCENT_SECRET_KEY` | 腾讯云控制台 → 访问管理 → API 密钥，并开通「语音识别」服务 |
| `DEEPSEEK_API_KEY` | <https://platform.deepseek.com> |
| `PROXY` | 国内网络必填，例如 `http://127.0.0.1:7897`。只有 YouTube 下载和 Gmail 走代理，腾讯云与 DeepSeek 始终直连 |
| `YTDLP_COOKIES_BROWSER` | YouTube 提示机器人验证时设置，如 `chrome`，从浏览器读登录 cookies |

3. 安装依赖：

```bash
uv sync
```

4. 配置发件邮箱（163，一次性）：

   登录 [163 邮箱网页版](https://mail.163.com) → 设置 → **POP3/SMTP/IMAP** → 开启 **SMTP 服务**，
   按提示获取「授权码」，填到 `.env`：

   ```
   SMTP_USER=你的邮箱@163.com
   SMTP_PASS=授权码   # 注意是授权码，不是登录密码
   ```

## 使用

### 命令行

```bash
# 完整流程（发邮件到 DEFAULT_RECIPIENT 或 --email 指定的邮箱）
uv run main.py run "https://www.youtube.com/watch?v=xxxx" --email you@example.com

# 只看总结不发邮件
uv run main.py run "https://www.youtube.com/watch?v=xxxx" --no-email
```

### 网站

```bash
uv run main.py serve            # http://127.0.0.1:8000
uv run main.py serve --host 0.0.0.0 --port 8000   # 局域网访问
```

网页上粘贴视频链接 + 收件邮箱，提交后可实时查看进度，完成后页面直接显示总结，邮箱也会收到一份。

## 实现说明

- **下载**：优先 yt-dlp 提取最佳音轨转 mp3（128kbps）。被 YouTube 风控拦截（"Sign in to confirm you're not a bot"）时自动回退到 Piped 公共实例（`PIPED_INSTANCES`），由实例服务器代理取流再用 ffmpeg 抽音频；也可配置 `YTDLP_COOKIES_BROWSER` / `YTDLP_COOKIES_FILE` 带登录态走 yt-dlp。`vendor/bgutil-ytdlp-pot-provider` 存在时自动启用 PO Token 增强
- **转写**：腾讯云「录音文件识别」本地上传限制 5MB，所以先用 ffmpeg 压成 16kHz 单声道 32kbps 并按 10 分钟切片，逐片识别后拼接，无需 COS
- **总结**：DeepSeek（OpenAI 兼容接口），超长转写按 `MAX_TRANSCRIPT_CHARS` 截断
- **邮件**：163 邮箱 SMTP（SSL 465，授权码登录），Markdown 渲染成 HTML 发送
- **网络分流**：`PROXY` 只作用于 yt-dlp / Piped 下载；腾讯云 ASR、DeepSeek、163 邮箱均直连国内网络
- **网站**：FastAPI，任务在后台线程执行，前端轮询 `/api/tasks/{id}` 显示进度；任务状态存内存，重启丢失
