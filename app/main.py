from http.client import HTTPException
from typing import List, Optional


from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from uuid import UUID, uuid4
from datetime import datetime
from app.services.model_service import ModelService
from app.services.queue_job_service import QueueJobService
from app.services.repository_service import RepositoryService


from app.models.model import ModelResponse  # Assumendo che il tuo modello sia in models.py
from app.models.model import PaginatedModelResponse  # Assumendo che il tuo modello sia in models.py
from app.models.model import ModelCreateRequest  # Assumendo che il tuo modello sia in models.py
from app.models.model import PresignedUrlRequest  # Assumendo che il tuo modello sia in models.py

app = FastAPI()
queue_job_service = QueueJobService()
model_service = ModelService()
repository_service = RepositoryService()

# Configura il middleware CORS
origins = [
    "http://localhost:5173",  # Frontend in esecuzione su questa porta
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Consenti le origini specificate
    allow_credentials=True,
    allow_methods=["*"],  # Permetti tutti i metodi HTTP (GET, POST, PUT, DELETE, ecc.)
    allow_headers=["*"],  # Permetti tutte le intestazioni
)


# 1️⃣ Endpoint per creare un nuovo modello
@app.post("/models/", response_model=ModelResponse)
async def create_model(request: ModelCreateRequest):
     try:
        # Chiama il servizio per creare il modello in MongoDB
        model = await model_service.create_model_in_db(request)
        print('MODEL:' + str(model))
        # Invia il job a RabbitMQ
        queue_job_service.send_job(model['_id'])
        return model
     except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2️⃣ Endpoint per ottenere la lista dei modelli con paginazione e sorting
@app.get("/models/", response_model=PaginatedModelResponse)
async def list_models(
    page: int = Query(1, alias="page", ge=1),
    limit: int = Query(10, alias="limit", ge=1, le=100),
    sort_by: Optional[str] = Query(None, regex="^(model_name|status|created_at)$"),
    order: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    title: Optional[str] = Query(None),  # Filtro per model_name
    status: Optional[List[str]] = Query(None)  # Filtro per status
):
    """
    Restituisce la lista dei modelli con paginazione, ordinamento e filtri opzionali.
    """
    try:
        models, total_count = model_service.list_models_from_db(
            page, limit, sort_by, order, title_filter=title, status_filter=status
        )
        
        # Calcoliamo il numero di pagine
        total_pages = (total_count + limit - 1) // limit  # Calcola il numero di pagine

        # Risposta con paginazione
        return PaginatedModelResponse(
            models=models,
            totalCount=total_count,
            totalPages=total_pages,
            page=page
        )
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
        model = model_service.get_model_by_id(model_id)
        if model is None:
            raise HTTPException(status_code=404, detail="Model not found")
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 1️⃣ Ottieni un Presigned URL per l'upload
@app.post("/s3/upload-url/")
async def get_upload_url(request: PresignedUrlRequest):
    """
    Genera un UUID per il modello e restituisce un URL presigned per l'upload.
    Il file verrà caricato dentro una cartella con il nome dell'UUID.
    """
    # 1️⃣ Genera UUID per la cartella del modello
    model_id = str(uuid4())
    s3_key = f"models/{model_id}/{request.filename}"  # File all'interno della cartella

    try:
        presigned_url = repository_service.generate_presigned_url_upload(
            s3_key,request.content_type
        )
       
        response = {"model_id": model_id, "upload_url": presigned_url,"video_uri": s3_key}
        # Logga la risposta
        print(f"RESPONSE: {response}")

        # 3️⃣ Restituisci UUID e URL per l'upload
        return response
    except Exception as e:
        print(f"ERRORE: {str(e)}")
        return {"error": str(e)}

    
@app.get("/health")
async def health_check():
    return {"status": "success", "message": "API is up and running!"}
