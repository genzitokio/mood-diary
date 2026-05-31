from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from db import MoodEntry, get_session, init_db
from ml import predict_sentiment
from recommend import get_recommendation
from schemas import MoodCreate, MoodCreated, MoodOut

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Mood Diary API", version="0.1.0", lifespan=lifespan)


@app.post("/entries", response_model=MoodCreated)
def create_entry(payload: MoodCreate, session: Session = Depends(get_session)) -> MoodCreated:
    label, score = predict_sentiment(payload.text)
    entry = MoodEntry(
        text=payload.text,
        emoji=payload.emoji,
        tag=payload.tag,
        sentiment_label=label,
        sentiment_score=score,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return MoodCreated(
        id=entry.id,
        created_at=entry.created_at,
        text=entry.text,
        emoji=entry.emoji,
        tag=entry.tag,
        sentiment_label=entry.sentiment_label,
        sentiment_score=entry.sentiment_score,
        recommendation=get_recommendation(label),
    )


@app.get("/entries", response_model=list[MoodOut])
def list_entries(
    session: Session = Depends(get_session),
    tag: str | None = None,
) -> list[MoodOut]:
    stmt = select(MoodEntry).order_by(MoodEntry.created_at.desc())
    if tag:
        stmt = stmt.where(MoodEntry.tag == tag.lower())
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
            func.sum(case((MoodEntry.sentiment_label == "positive", 1), else_=0)).label("pos"),
            func.sum(case((MoodEntry.sentiment_label == "negative", 1), else_=0)).label("neg"),
            func.sum(case((MoodEntry.sentiment_label == "neutral", 1), else_=0)).label("neu"),
        )
        .group_by(day)
        .order_by(day)
    )
    rows = session.execute(stmt).all()
    return [
        {
            "day": r.day,
            "count": r.count,
            "avg_score": float(r.avg_score or 0.0),
            "positive": int(r.pos or 0),
            "negative": int(r.neg or 0),
            "neutral": int(r.neu or 0),
        }
        for r in rows
    ]


@app.get("/analytics/weekday")
def analytics_weekday(session: Session = Depends(get_session)) -> list[dict]:
    """Срез по дням недели — как в примере кейса: 'усталость в понедельники'.

    Группировка идёт по UTC-дате (так хранится created_at). Возможен
    небольшой сдвиг на границе суток в иных таймзонах — для прототипа ОК.
    """
    # SQLite strftime('%w') → 0=вс, 1=пн ... 6=сб
    wd = func.strftime("%w", MoodEntry.created_at)
    stmt = (
        select(
            wd.label("wd"),
            func.count(MoodEntry.id).label("count"),
            func.avg(MoodEntry.sentiment_score).label("avg_score"),
        )
        .group_by(wd)
    )
    rows = {r.wd: r for r in session.execute(stmt).all()}

    names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    # выводим в порядке Пн..Вс
    out = []
    for idx, name in enumerate(names):
        key = str(idx + 1) if idx < 6 else "0"  # 0=вс в SQLite
        r = rows.get(key)
        out.append({
            "weekday": name,
            "count": int(r.count) if r else 0,
            "avg_score": float(r.avg_score) if r and r.avg_score is not None else 0.0,
        })
    return out


@app.get("/analytics/tags")
def analytics_tags(session: Session = Depends(get_session)) -> list[dict]:
    """Связь настроения с событиями: средний score по каждому тегу.

    Это и есть «анализ изменений в настроении (связь с событиями)» из кейса.
    Например: tag='работа' → avg_score=-0.4, tag='спорт' → avg_score=+0.7.
    """
    stmt = (
        select(
            MoodEntry.tag,
            func.count(MoodEntry.id).label("count"),
            func.avg(MoodEntry.sentiment_score).label("avg_score"),
        )
        .where(MoodEntry.tag.is_not(None))
        .group_by(MoodEntry.tag)
        .order_by(func.avg(MoodEntry.sentiment_score).desc())
    )
    return [
        {
            "tag": tag,
            "count": int(count),
            "avg_score": float(avg or 0.0),
        }
        for tag, count, avg in session.execute(stmt).all()
    ]


@app.get("/analytics/summary")
def analytics_summary(session: Session = Depends(get_session)) -> dict:
    counts_stmt = (
        select(MoodEntry.sentiment_label, func.count(MoodEntry.id))
        .group_by(MoodEntry.sentiment_label)
    )
    by_label = {
        (label or "neutral"): count
        for label, count in session.execute(counts_stmt).all()
    }

    total = sum(by_label.values())
    avg_row = session.execute(
        select(func.avg(MoodEntry.sentiment_score))
    ).scalar()

    first_day, last_day = session.execute(
        select(
            func.min(func.date(MoodEntry.created_at)),
            func.max(func.date(MoodEntry.created_at)),
        )
    ).one()

    return {
        "total": total,
        "avg_score": float(avg_row or 0.0),
        "by_label": {
            "positive": by_label.get("positive", 0),
            "neutral": by_label.get("neutral", 0),
            "negative": by_label.get("negative", 0),
        },
        "first_day": first_day,
        "last_day": last_day,
    }


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"name": "Mood Diary API", "docs": "/docs"})
