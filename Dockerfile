FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY evals ./evals

ENV LLM_PROVIDER=mock \
    DB_PATH=/app/data/content_factory.db \
    PUBLISH_DRY_RUN=true

EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
