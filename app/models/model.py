# app/models/model.py
from pydantic import BaseModel, HttpUrl,Field
from uuid import UUID
from datetime import datetime
from typing import List

class ModelResponse(BaseModel):
    id: str = Field(alias='_id')
    video_uri: str
    thumbnail_s3_key: str
    thumbnail_url: str
    title: str
    output_s3_key: str
    output_url: str
    status: str
    created_at: datetime
    updated_at: datetime

class PaginatedModelResponse(BaseModel):
    models: List[ModelResponse]
    totalCount: int
    totalPages: int
    page: int

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

