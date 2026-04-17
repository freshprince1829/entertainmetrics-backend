from collections.abc import Mapping

from sqlalchemy.orm import Session

from . import models, schemas


def create_event(db: Session, event: schemas.EventCreate):
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_events(db: Session):
    return (
        db.query(models.Event)
        .order_by(models.Event.event_date.desc(), models.Event.id.desc())
        .all()
    )


def create_artist(db: Session, artist: schemas.ArtistCreate):
    db_artist = models.Artist(**artist.model_dump())
    db.add(db_artist)
    db.commit()
    db.refresh(db_artist)
    return db_artist


def get_artists(db: Session):
    return db.query(models.Artist).order_by(models.Artist.artist_name.asc()).all()


def create_event_artist(db: Session, event_artist: schemas.EventArtistCreate):
    db_event_artist = models.EventArtist(**event_artist.model_dump())
    db.add(db_event_artist)
    db.commit()
    db.refresh(db_event_artist)
    return db_event_artist


def get_event_lineup(db: Session, event_id: int):
    return (
        db.query(models.EventArtist)
        .filter(models.EventArtist.event_id == event_id)
        .order_by(models.EventArtist.performance_order.asc(), models.EventArtist.id.asc())
        .all()
    )


def create_prediction(
    db: Session,
    prediction_data: Mapping[str, object] | None = None,
    **kwargs,
):
    payload = dict(prediction_data or {})
    payload.update(kwargs)

    db_prediction = models.Prediction(**payload)
    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    return db_prediction


def get_predictions(db: Session):
    return db.query(models.Prediction).order_by(models.Prediction.id.desc()).all()
