from sqlalchemy.orm import Session
from . import models, schemas


def create_event(db: Session, event: schemas.EventCreate):
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_events(db: Session):
    return db.query(models.Event).order_by(models.Event.id.desc()).all()


def create_prediction(db: Session, prediction_data: dict):
    db_prediction = models.Prediction(**prediction_data)
    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    return db_prediction


def get_predictions(db: Session):
    return db.query(models.Prediction).order_by(models.Prediction.id.desc()).all()