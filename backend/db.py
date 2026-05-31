import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Integer, String, Float, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_PATH = os.getenv("DB_PATH", "./mood.db")
DB_URL = f"sqlite:///{DB_PATH}"


def _utcnow() -> datetime:
    # БД хранит naive datetime; пишем naive UTC, сериализатор в schemas.py
    # добавит суффикс Z при выдаче клиенту.
    return datetime.now(timezone.utc).replace(tzinfo=None)


engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class MoodEntry(Base):
    __tablename__ = "mood_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    text: Mapped[str] = mapped_column(String(2000))
    emoji: Mapped[str | None] = mapped_column(String(8), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
