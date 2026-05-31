"""Sentiment analysis.

День 1: заглушка (всегда neutral).
День 2: подменим на pipeline transformers.
"""


def predict_sentiment(text: str) -> tuple[str, float]:
    return "neutral", 0.0
