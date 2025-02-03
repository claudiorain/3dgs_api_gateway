from http.client import HTTPException
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from uuid import UUID, uuid4
from datetime import datetime
from services.model_service import create_model_in_db

app = FastAPI()

# Modello dati
class ModelCreateRequest(BaseModel):
    video_url: HttpUrl
    model_name: str

# Modello per la risposta
class ModelResponse(BaseModel):
    id: UUID
    video_url: HttpUrl
    model_name: str
    model_folder_url: str
    status: str
    created_at: datetime
    updated_at: datetime

# 1️⃣ Endpoint per creare un nuovo modello
@app.post("/models/", response_model=ModelResponse)
async def create_model(request: ModelCreateRequest):
     try:
        # Chiama il servizio per creare il modello in MongoDB
        model = await create_model_in_db(request)
        return model
     except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2️⃣ Endpoint per ottenere la lista dei modelli con paginazione e sorting
@app.get("/models/", response_model=List[ModelResponse])
async def list_models(
    page: int = Query(1, alias="page", ge=1),
    limit: int = Query(10, alias="limit", ge=1, le=100),
    sort_by: Optional[str] = Query(None, regex="^(model_name|status)$"),
    order: Optional[str] = Query("asc", regex="^(asc|desc)$")
):
    """
    Restituisce la lista dei modelli con paginazione e ordinamento opzionale.
    """
    pass  # Implementazione futura

# 3️⃣ Endpoint per eliminare un modello tramite ID
@app.delete("/models/{model_id}", response_model=dict)
async def delete_model(model_id: UUID):
    """
    Elimina un modello dal database.
    """
    pass  # Implementazione futura
