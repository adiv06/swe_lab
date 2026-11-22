# Production image: builds the React frontend, then serves it from FastAPI on
# the same origin as /api (so the hw_session login cookie works without CORS).

# ---- Stage 1: build the frontend ----
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python API + built static files ----
FROM python:3.12-slim
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# app/main.py serves frontend/dist relative to the working directory
COPY --from=frontend /frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE 8000
# Render and most hosts inject $PORT; default to 8000 locally
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
