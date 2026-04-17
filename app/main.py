from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from . import schemas, crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EntertainMetrics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/predict", response_model=schemas.PredictionResponse)
def predict_event(data: schemas.PredictionRequest, db: Session = Depends(get_db)):
    predicted_attendance = int(
        min(
            data.capacity,
            (data.marketing_spend / 50) + (data.capacity * 0.45) - (data.ticket_price / 20)
        )
    )

    if predicted_attendance < 0:
        predicted_attendance = 0

    predicted_revenue = round(predicted_attendance * data.ticket_price, 2)
    confidence_score = 0.78

    prediction_record = {
        "event_name": data.event_name,
        "predicted_attendance": predicted_attendance,
        "predicted_revenue": predicted_revenue,
        "confidence_score": confidence_score,
    }

    crud.create_prediction(db, prediction_record)

    return prediction_record


@app.get("/predictions")
def list_predictions(db: Session = Depends(get_db)):
    return crud.get_predictions(db)