# Two stages: build the React bundle with Node, then serve it plus the API
# from Python. One image, one process, one port — which keeps free-tier
# hosting (Railway, Render, Fly) straightforward.

FROM node:20-alpine AS web
WORKDIR /build
COPY web/package.json web/package-lock.json* ./
RUN npm ci --omit=dev || npm install
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    COUNTY_DATA_DIR=/data

# The audit ledger is the one thing the app writes that must outlive a
# deploy. A container filesystem does not, so this path expects a mounted
# volume. Without one the app still runs — the history simply resets, and
# /health says so rather than failing quietly.
VOLUME ["/data"]

# Dependencies first, so code edits do not invalidate the layer.
COPY pyproject.toml ./
# python-multipart is not optional: the upload routes import it, so omitting
# it makes the container fail at start rather than at first request.
RUN pip install --no-cache-dir \
      "fastapi>=0.110,<1.0" "uvicorn[standard]>=0.29,<1.0" \
      "python-multipart>=0.0.9,<1.0" "pyyaml>=6" "python-docx>=1.1,<2.0"

COPY search_authority/ ./search_authority/
COPY api/ ./api/
COPY county_context/ ./county_context/
COPY blogs/BLOG_INVENTORY.yaml ./blogs/BLOG_INVENTORY.yaml
COPY --from=web /build/dist ./web/dist

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",8000)}/health', timeout=4).status==200 else 1)"

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
