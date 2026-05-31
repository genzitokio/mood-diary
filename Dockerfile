FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TRANSFORMERS_NO_ADVISORY_WARNINGS=1

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt

# torch ставим из CPU-индекса, остальное — обычно
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch \
 && pip install -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

# Прогрев: скачать модель внутрь образа, чтобы первый POST не тормозил
RUN python -c "from transformers import pipeline; \
    pipeline('sentiment-analysis', model='cardiffnlp/twitter-xlm-roberta-base-sentiment', \
             model_kwargs={'cache_dir': '/app/backend/models_cache'})"

EXPOSE 8000

WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
