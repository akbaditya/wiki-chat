# ---- stage 1: build the React app ----
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- stage 2: API + the built frontend, one container ----
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_XET=1 HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    MODELS_PATH=/app/models FRONTEND_DIST=/app/static PORT=7860
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
# download the embedding + reranker models at build time, so the first request is fast
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/app/models'); from flashrank import Ranker; Ranker(model_name='ms-marco-MiniLM-L-12-v2', cache_dir='/app/models')"
COPY backend/app ./app
COPY --from=web /web/dist ./static
RUN useradd -m -u 1000 app && mkdir -p data && chown -R app:app /app
USER app
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]