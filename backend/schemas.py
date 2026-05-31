from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class MoodCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    emoji: str | None = Field(default=None, max_length=8)


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
