# Translator Service for Option 1

This folder now contains a FastAPI translator service for GKE deployment.

## API

- `GET /healthz`
- `POST /detect-language`
- `POST /translate`

Supported languages only:

- `en`, `es`, `fr`, `it`

## Local Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Docker

```bash
docker build -t translator:local .
docker run --rm -p 8000:8000 translator:local
```
