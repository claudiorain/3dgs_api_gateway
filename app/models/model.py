# app/models/model.py
from pydantic import BaseModel, HttpUrl,Field
from uuid import UUID
from datetime import datetime

class ModelResponse(BaseModel):
    id: str = Field(alias='_id')
    video_url: HttpUrl
    model_name: str
    model_folder_url: str
    status: str
    created_at: datetime
    updated_at: datetime
