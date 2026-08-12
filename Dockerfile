FROM python:3.12-slim

# 国内环境：apt 换腾讯云镜像源（海外构建可删掉 sed 这行）
RUN sed -i 's|deb.debian.org|mirrors.cloud.tencent.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl unzip \
    && rm -rf /var/lib/apt/lists/*

# deno：yt-dlp EJS n-challenge 解密的 JS runtime（apt 的 node 20 版本太老，yt-dlp 标记 unsupported）
# 国内构建 dl.deno.land 直连极慢，由 compose 传入 DENO_DL_PROXY 走宿主机代理下载
ARG DENO_VERSION=2.2.0
ARG DENO_DL_PROXY
RUN curl -fsSL ${DENO_DL_PROXY:+-x "$DENO_DL_PROXY"} \
        -o /tmp/deno.zip "https://dl.deno.land/release/v${DENO_VERSION}/deno-x86_64-unknown-linux-gnu.zip" \
    && unzip -o /tmp/deno.zip -d /usr/local/bin \
    && rm /tmp/deno.zip \
    && deno --version

WORKDIR /app

RUN pip install --no-cache-dir uv

# 先装依赖再拷代码，让依赖层可以缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "main.py", "serve", "--host", "0.0.0.0", "--port", "8000"]
