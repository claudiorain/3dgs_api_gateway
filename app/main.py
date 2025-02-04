from http.client import HTTPException
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from uuid import UUID, uuid4
from datetime import datetime
from app.services.model_service import create_model_in_db
from app.services.model_service import get_model_by_id

from app.models.model import ModelResponse  # Assumendo che il tuo modello sia in models.py

app = FastAPI()

# Modello dati
class ModelCreateRequest(BaseModel):
    video_url: str  
    model_name: str

    class Config:
        # Imposta come serializzare HttpUrl
        json_encoders = {
            HttpUrl: lambda v: str(v)  # Converti il tipo HttpUrl in stringa
        }

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
    sort_by: Optional[str] = Query(None, regex="^(model_name|status|created_at)$"),
    order: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    model_name: Optional[str] = Query(None),  # Filtro per model_name
    status: Optional[List[str]] = Query(None)  # Filtro per status
):
    """
    Restituisce la lista dei modelli con paginazione, ordinamento e filtri opzionali.
    """
    try:
        models = await list_models_from_db(
            page, limit, sort_by, order, model_name_filter=model_name, status_filter=status
        )
        return models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 3️⃣ Endpoint per eliminare un modello tramite ID
@app.delete("/models/{model_id}", response_model=dict)
async def delete_model(model_id: UUID):
    """
    Elimina un modello dal database.
    """
    pass  # Implementazione futura

@app.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(model_id: UUID):
    """
    Recupera un modello dal database tramite l'ID.
    """
    try:
        # Chiama il servizio per ottenere il modello dal database
        model = await get_model_by_id(model_id)
        if model is None:
            raise HTTPException(status_code=404, detail="Model not found")
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "success", "message": "API is up and running!"}