from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from .database import Base, engine, get_db
from . import crud, models, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EntertainMetrics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _calculate_artist_strength_total(event: models.Event) -> float:
    total = 0.0

    for lineup_entry in event.lineup:
        artist = lineup_entry.artist
        if artist is None:
            continue

        total += (
            float(artist.engagement_score or 0)
            + float(artist.headline_score or 0)
            + float(artist.market_strength_score or 0)
        )

    return total


def _constraint_name(error: IntegrityError) -> str | None:
    diag = getattr(getattr(error, "orig", None), "diag", None)
    return getattr(diag, "constraint_name", None)


def _rollback_and_raise(
    db: Session,
    status_code: int,
    detail: str,
    error: Exception,
) -> None:
    db.rollback()
    raise HTTPException(status_code=status_code, detail=detail) from error


def _handle_artist_creation_error(db: Session, error: IntegrityError) -> None:
    constraint_name = _constraint_name(error)
    error_message = str(getattr(error, "orig", error)).lower()

    if constraint_name == "artists_artist_name_key" or (
        "artist_name" in error_message and "unique" in error_message
    ):
        _rollback_and_raise(db, 400, "Artist already exists", error)

    _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


def _handle_event_artist_creation_error(db: Session, error: IntegrityError) -> None:
    constraint_name = _constraint_name(error)
    error_message = str(getattr(error, "orig", error)).lower()

    if constraint_name == "uq_event_artist_performance_order":
        _rollback_and_raise(
            db,
            400,
            "This artist is already assigned to this event slot",
            error,
        )

    if "foreign key" in error_message:
        _rollback_and_raise(db, 404, "Referenced event or artist does not exist", error)

    _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.get("/")
def root():
    return {"message": "EntertainMetrics backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "EntertainMetrics API"}


@app.post("/events", response_model=schemas.EventResponse)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_event(db, event)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.get("/events", response_model=list[schemas.EventResponse])
def list_events(db: Session = Depends(get_db)):
    try:
        return crud.get_events(db)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.post("/artists", response_model=schemas.ArtistResponse)
def create_artist(artist: schemas.ArtistCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_artist(db, artist)
    except IntegrityError as error:
        _handle_artist_creation_error(db, error)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.get("/artists", response_model=list[schemas.ArtistResponse])
def list_artists(db: Session = Depends(get_db)):
    try:
        return crud.get_artists(db)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.post("/event-artists", response_model=schemas.EventArtistResponse)
def create_event_artist(
    event_artist: schemas.EventArtistCreate,
    db: Session = Depends(get_db),
):
    try:
        return crud.create_event_artist(db, event_artist)
    except IntegrityError as error:
        _handle_event_artist_creation_error(db, error)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.get("/events/{event_id}/lineup", response_model=list[schemas.EventArtistResponse])
def get_event_lineup(event_id: int, db: Session = Depends(get_db)):
    try:
        return crud.get_event_lineup(db, event_id)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.post("/predict", response_model=schemas.PredictionResponse)
def predict_event(data: schemas.PredictionRequest, db: Session = Depends(get_db)):
    try:
        event = (
            db.query(models.Event)
            .options(
                selectinload(models.Event.lineup).selectinload(models.EventArtist.artist)
            )
            .filter(models.Event.id == data.event_id)
            .first()
        )
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")

        artist_strength_total = _calculate_artist_strength_total(event)
        predicted_attendance = int(
            min(
                data.capacity,
                (data.capacity * 0.4)
                + (data.marketing_spend / 50)
                + (artist_strength_total * 10)
                - (data.ticket_price / 20),
            )
        )
        predicted_attendance = max(predicted_attendance, 0)

        predicted_revenue = round(predicted_attendance * data.ticket_price, 2)
        confidence_score = 0.78
        model_version = "v1-rule-based"
        insight_summary = (
            f"Rule-based estimate using {len(event.lineup)} linked artists with a total "
            f"strength score of {artist_strength_total:.2f}, plus pricing, marketing, "
            "and venue capacity."
        )

        prediction_record = {
            "event_id": data.event_id,
            "predicted_attendance": predicted_attendance,
            "predicted_revenue": predicted_revenue,
            "confidence_score": confidence_score,
            "model_version": model_version,
            "insight_summary": insight_summary,
        }

        return crud.create_prediction(db, prediction_record)
    except HTTPException:
        raise
    except IntegrityError as error:
        error_message = str(getattr(error, "orig", error)).lower()
        if "foreign key" in error_message:
            _rollback_and_raise(db, 404, "Referenced event or artist does not exist", error)
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.get("/predictions", response_model=list[schemas.PredictionResponse])
def list_predictions(db: Session = Depends(get_db)):
    try:
        return crud.get_predictions(db)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.get("/dashboard/summary", response_model=schemas.DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    try:
        return crud.get_dashboard_summary(db)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.get("/dashboard/recent-events", response_model=list[schemas.RecentEventResponse])
def get_recent_events(limit: int = 5, db: Session = Depends(get_db)):
    try:
        return crud.get_recent_events(db, limit=limit)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)


@app.get(
    "/dashboard/recent-predictions",
    response_model=list[schemas.RecentPredictionResponse],
)
def get_recent_predictions(limit: int = 5, db: Session = Depends(get_db)):
    try:
        return crud.get_recent_predictions(db, limit=limit)
    except SQLAlchemyError as error:
        _rollback_and_raise(db, 500, "An unexpected database error occurred", error)
