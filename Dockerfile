FROM python:3.12-slim

# 国内环境：apt 换腾讯云镜像源（海外构建可删掉 sed 这行）
RUN sed -i 's|deb.debian.org|mirrors.cloud.tencent.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir uv

# 先装依赖再拷代码，让依赖层可以缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "main.py", "serve", "--host", "0.0.0.0", "--port", "8000"]
