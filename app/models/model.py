# app/models/model.py
from pydantic import BaseModel, HttpUrl,Field
from uuid import UUID
from datetime import datetime

class ModelResponse(BaseModel):
    id: str = Field(alias='_id')
    video_uri: str
    title: str
    output_path: str
    status: str
    created_at: datetime
    updated_at: datetime

# Modello dati
class ModelCreateRequest(BaseModel):
    model_id: str
    video_uri: str  
    title: str

    class Config:
        # Imposta come serializzare HttpUrl
        json_encoders = {
            HttpUrl: lambda v: str(v)  # Converti il tipo HttpUrl in stringa
        }

class PresignedUrlRequest(BaseModel):
    filename: str  # Nome del file che si vuole caricare
    content_type: str  # Tipo di contenuto (es. "image/png", "application/pdf")

