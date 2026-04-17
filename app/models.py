from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String, nullable=False)
    venue = Column(String, nullable=False)
    city = Column(String, nullable=False)
    ticket_price = Column(Float, nullable=False)
    marketing_spend = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False)
    actual_attendance = Column(Integer, nullable=True)
    revenue = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String, nullable=False)
    predicted_attendance = Column(Integer, nullable=False)
    predicted_revenue = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())