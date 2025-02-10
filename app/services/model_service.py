from uuid import uuid4
from uuid import UUID
from datetime import datetime
from app.config.db import get_database  # Assicurati che questa funzione restituisca il client del database
from app.models.model import ModelResponse  # Assumendo che il tuo modello sia in models.py
from typing import List, Optional
from pymongo import ASCENDING, DESCENDING
from app.models.model import ModelCreateRequest  # Assumendo che il tuo modello sia in models.py

# Configurazione MongoDB

# Esempio di connessione al DB
class ModelService:

    def __init__(self):
        """Inizializza la connessione a MongoDB."""
        self.db = get_database()  # Ottieni il database con il client asincrono

    # Funzione per creare un modello nel DB
    async def create_model_in_db(self, request: ModelCreateRequest):

        model_id = request.model_id
        current_time = datetime.utcnow()

        # Documento da inserire in MongoDB
        model_data = {
            "_id": model_id,
            "filename": request.filename,
            "model_name": request.model_name,
            "model_output_path": "",  # Vuoto per ora
            "status": "QUEUED",
            "created_at": current_time,
            "updated_at": current_time
        }

        try:
            result = self.db["models"].insert_one(model_data)
            print(f"Inserted document ID: {result.inserted_id}")
            return model_data
        except Exception as e:
            print(f"Error inserting document: {e}")
            raise

    async def get_model_by_id(self, model_id: UUID) -> ModelResponse:
        """
        Recupera un modello dal database usando l'ID.
        """
        # Supponiamo che tu abbia una collezione 'models' nel tuo database MongoDB
        model = self.db['models'].find_one({"_id": str(model_id)})
        
        # Se il modello non esiste
        if model is None:
            return None

        # Restituisci un oggetto del tipo ModelResponse
        return ModelResponse(
            _id=model['_id'],
            filename=model['filename'],
            model_name=model['model_name'],
            model_output_path=model['model_output_path'],
            status=model['status'],
            created_at=model['created_at'],
            updated_at=model['updated_at']
        )

    async def list_models_from_db(self,
        page: int,
        limit: int,
        sort_by: Optional[str],
        order: Optional[str],
        model_name_filter: Optional[str] = None,  # Filtro per model_name
        status_filter: Optional[List[str]] = None  # Filtro per status
    ) -> List[ModelResponse]:

        # Imposta il campo di ordinamento
        if sort_by == "model_name":
            sort_field = "model_name"
        elif sort_by == "status":
            sort_field = "status"
        else:
            sort_field = "created_at"  # Default sorting by created_at

        # Imposta l'ordine dell'ordinamento
        sort_order = ASCENDING if order == "asc" else DESCENDING

        # Paginazione: calcola l'offset
        skip = (page - 1) * limit

        # Costruisci il filtro
        filters = {}

        if model_name_filter:
            filters["model_name"] = {"$regex": model_name_filter, "$options": "i"}  # Filtro LIKE (case-insensitive)

        if status_filter:
            filters["status"] = {"$in": status_filter}  # Filtro OR sui status (match con uno dei valori)

        # Esegui la query con filtri, paginazione e ordinamento
        models_cursor = db['models'].find(filters).sort(sort_field, sort_order).skip(skip).limit(limit)

        models = []
        for model in models_cursor:  # Iterazione sincrona (non asincrona)
            models.append(ModelResponse(
                _id=model['_id'],
                filename=model['filename'],
                model_name=model['model_name'],
                model_output_path=model['model_output_path'],
                status=model['status'],
                created_at=model['created_at'],
                updated_at=model['updated_at']
            ))

        return models
