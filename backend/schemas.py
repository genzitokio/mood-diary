from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class MoodCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    emoji: str | None = Field(default=None, max_length=8)

    @field_validator("text", mode="after")
    @classmethod
    def _text_must_be_non_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be blank")
        return v

    @field_validator("emoji", mode="after")
    @classmethod
    def _empty_emoji_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class MoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    text: str
    emoji: str | None
    sentiment_label: str | None
    sentiment_score: float | None

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        # БД (SQLite) хранит naive datetime; в БД мы пишем UTC, поэтому
        # достраиваем суффикс Z, чтобы фронт корректно сконвертировал в локаль.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")


class MoodCreated(MoodOut):
    recommendation: str | None = None
