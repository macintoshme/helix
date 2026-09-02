# frontend build
FROM node:20.20.2-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

# backend/runtime
FROM python:3.11-slim

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    flac \
    ca-certificates \
    git \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# deno for yt-dlp (pinned release + SHA256)
ARG DENO_VERSION=2.9.6
RUN curl -fsSL "https://github.com/denoland/deno/releases/download/v${DENO_VERSION}/deno-x86_64-unknown-linux-gnu.zip" -o /tmp/deno.zip \
    && echo "394f07f4da2bebe6ce6f1e7ce0fa16429b29b08c35e3fac3fe25972676dff4b2  /tmp/deno.zip" | sha256sum -c - \
    && unzip -o /tmp/deno.zip -d /usr/local/bin \
    && rm /tmp/deno.zip \
    && chmod +x /usr/local/bin/deno

# backend deps
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# beets
RUN pip install --no-cache-dir beets

# backend code
COPY backend/app ./app

# default configs copied into image, then copied into /data on first run
COPY backend/defaults/beets/config.yaml /app/defaults/beets/config.yaml
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# built frontend only
COPY --from=frontend-build /frontend/dist ./static

ENV MR_DB_PATH=/data/app.db
EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]