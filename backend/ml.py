"""Sentiment analysis.

Используем готовую мультиязычную модель cardiffnlp/twitter-xlm-roberta-base-sentiment
(обучена твитах на 8 языках, включая русский). НЕ дообучаем — берём как есть.

Модель возвращает один из лейблов: negative / neutral / positive + score [0..1].
В sentiment_score кладём знаковую величину (-prob / 0 / +prob), чтобы
среднее в /analytics/daily имело смысл "настроение дня".
"""

from __future__ import annotations

import os
from threading import Lock
from typing import Any

MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "models_cache")

_pipeline: Any | None = None
_lock = Lock()


def _get_pipeline() -> Any:
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    with _lock:
        if _pipeline is None:
            from transformers import pipeline

            os.makedirs(CACHE_DIR, exist_ok=True)
            _pipeline = pipeline(
                task="sentiment-analysis",
                model=MODEL_NAME,
                tokenizer=MODEL_NAME,
                model_kwargs={"cache_dir": CACHE_DIR},
            )
    return _pipeline


def predict_sentiment(text: str) -> tuple[str, float]:
    text = (text or "").strip()
    if not text:
        return "neutral", 0.0

    result = _get_pipeline()(text[:512], truncation=True)[0]
    label = str(result["label"]).lower()
    prob = float(result["score"])

    if label == "positive":
        return "positive", prob
    if label == "negative":
        return "negative", -prob
    return "neutral", 0.0


def warmup() -> None:
    """Прогрев модели на старте, чтобы первый POST не тормозил."""
    _get_pipeline()
