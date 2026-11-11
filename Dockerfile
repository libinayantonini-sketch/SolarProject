# Imagem única: compila o front (React) e serve tudo pela API (FastAPI). Build: docker compose build
FROM node:22-slim AS front
WORKDIR /f
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
COPY --from=front /f/dist /app/frontend_dist
ENV FRONTEND_DIR=/app/frontend_dist STORAGE_DIR=/data/images
RUN useradd -r -u 10001 app && mkdir -p /data/images && chown -R app /data
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
