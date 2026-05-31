from datetime import datetime
from pydantic import BaseModel, Field


class MoodCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    emoji: str | None = Field(default=None, max_length=8)


class MoodOut(BaseModel):
    id: int
    created_at: datetime
    text: str
    emoji: str | None
    sentiment_label: str | None
    sentiment_score: float | None

    class Config:
        from_attributes = True
