from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/")
def root():
    return {"message": "EntertainMetrics backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "EntertainMetrics API"}


@app.post("/events", response_model=schemas.EventResponse)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    return crud.create_event(db, event)


@app.get("/events", response_model=list[schemas.EventResponse])
def list_events(db: Session = Depends(get_db)):
    return crud.get_events(db)


@app.post("/artists", response_model=schemas.ArtistResponse)
def create_artist(artist: schemas.ArtistCreate, db: Session = Depends(get_db)):
    return crud.create_artist(db, artist)


@app.get("/artists", response_model=list[schemas.ArtistResponse])
def list_artists(db: Session = Depends(get_db)):
    return crud.get_artists(db)


@app.post("/event-artists", response_model=schemas.EventArtistResponse)
def create_event_artist(
    event_artist: schemas.EventArtistCreate,
    db: Session = Depends(get_db),
):
    return crud.create_event_artist(db, event_artist)


@app.get("/events/{event_id}/lineup", response_model=list[schemas.EventArtistResponse])
def get_event_lineup(event_id: int, db: Session = Depends(get_db)):
    return crud.get_event_lineup(db, event_id)


@app.post("/predict", response_model=schemas.PredictionResponse)
def predict_event(data: schemas.PredictionRequest, db: Session = Depends(get_db)):
    event = (
        db.query(models.Event)
        .options(selectinload(models.Event.lineup).selectinload(models.EventArtist.artist))
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

    saved_prediction = crud.create_prediction(db, prediction_record)
    return saved_prediction


@app.get("/predictions", response_model=list[schemas.PredictionResponse])
def list_predictions(db: Session = Depends(get_db)):
    return crud.get_predictions(db)
