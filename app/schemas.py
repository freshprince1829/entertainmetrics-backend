from pydantic import BaseModel

class EventCreate(BaseModel):
    event_name: str
    venue: str
    city: str
    ticket_price: float
    marketing_spend: float
    capacity: int
    actual_attendance: int | None = None
    revenue: float | None = None


class EventResponse(BaseModel):
    id: int
    event_name: str
    venue: str
    city: str
    ticket_price: float
    marketing_spend: float
    capacity: int
    actual_attendance: int | None = None
    revenue: float | None = None

    class Config:
        from_attributes = True


class PredictionRequest(BaseModel):
    event_name: str
    ticket_price: float
    marketing_spend: float
    capacity: int


class PredictionResponse(BaseModel):
    event_name: str
    predicted_attendance: int
    predicted_revenue: float
    confidence_score: float