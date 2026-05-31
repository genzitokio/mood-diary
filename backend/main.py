import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import MoodEntry, get_session, init_db
from ml import predict_sentiment, warmup
from schemas import MoodCreate, MoodOut

app = FastAPI(title="Mood Diary API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    if os.getenv("ML_WARMUP", "0") == "1":
        warmup()


@app.post("/entries", response_model=MoodOut)
def create_entry(payload: MoodCreate, session: Session = Depends(get_session)) -> MoodEntry:
    label, score = predict_sentiment(payload.text)
    entry = MoodEntry(
        text=payload.text,
        emoji=payload.emoji,
        sentiment_label=label,
        sentiment_score=score,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@app.get("/entries", response_model=list[MoodOut])
def list_entries(session: Session = Depends(get_session)) -> list[MoodEntry]:
    stmt = select(MoodEntry).order_by(MoodEntry.created_at.desc())
    return list(session.scalars(stmt).all())


@app.delete("/entries/{entry_id}")
def delete_entry(entry_id: int, session: Session = Depends(get_session)) -> dict:
    entry = session.get(MoodEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="entry not found")
    session.delete(entry)
    session.commit()
    return {"ok": True, "deleted_id": entry_id}


@app.get("/analytics/daily")
def analytics_daily(session: Session = Depends(get_session)) -> list[dict]:
    day = func.date(MoodEntry.created_at)
    stmt = (
        select(
            day.label("day"),
            func.count(MoodEntry.id).label("count"),
            func.avg(MoodEntry.sentiment_score).label("avg_score"),
        )
        .group_by(day)
        .order_by(day)
    )
    rows = session.execute(stmt).all()
    return [
        {"day": r.day, "count": r.count, "avg_score": float(r.avg_score or 0.0)}
        for r in rows
    ]


@app.get("/")
def root() -> dict:
    return {"name": "Mood Diary API", "docs": "/docs"}
