"""入口：

  uv run main.py run <YouTube链接> [--email 收件人]   # 命令行跑一次完整流程
  uv run main.py serve [--host 0.0.0.0] [--port 8000]  # 启动网站
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube 视频总结工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="对单个视频执行 下载→转写→总结→发邮件")
    run_p.add_argument("url", help="YouTube 视频链接")
    run_p.add_argument("--email", default="", help="收件邮箱，默认用 DEFAULT_RECIPIENT")
    run_p.add_argument("--no-email", action="store_true", help="只输出总结，不发邮件")

    serve_p = sub.add_parser("serve", help="启动 Web 服务")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.cmd == "run":
        from app import pipeline
        from app.config import settings

        recipient = "" if args.no_email else (args.email or settings.default_recipient)
        result = pipeline.run(args.url, recipient, on_progress=lambda s: print(f"==> {s}"))
        print(f"\n标题：{result['title']}\n")
        print(result["summary"])
        if recipient:
            if result.get("email_error"):
                print(f"\n⚠️ 邮件发送失败: {result['email_error']}")
            else:
                print(f"\n已发送至 {recipient}")
    elif args.cmd == "serve":
        import uvicorn

        uvicorn.run("app.web:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
