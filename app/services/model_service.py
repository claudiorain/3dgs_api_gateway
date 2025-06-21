from uuid import uuid4
from uuid import UUID
from datetime import datetime
from app.config.db import get_database  # Assicurati che questa funzione restituisca il client del database
from app.models.model import ModelResponse  # Assumendo che il tuo modello sia in models.py
from typing import List, Optional, Tuple
from pymongo import ASCENDING, DESCENDING
from app.models.model import ModelCreateRequest  # Assumendo che il tuo modello sia in models.py
from app.services.repository_service import RepositoryService
# Configurazione MongoDB

repository_service = RepositoryService()

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
            "video_s3_key": request.video_s3_key,
            "title": request.title,
            "description": request.description,
            "status": "QUEUED",
            "engine": request.engine,
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

    def get_model_by_id(self, model_id: UUID) -> ModelResponse:
        """
        Recupera un modello dal database usando l'ID.
        """
        # Supponiamo che tu abbia una collezione 'models' nel tuo database MongoDB
        model = self.db['models'].find_one({"_id": str(model_id)})
        
        # Se il modello non esiste
        if model is None:
            return None

        thumbnail_s3_key = model.get('thumbnail_s3_key', None)
        output_s3_key = model.get('output_s3_key', None)
        error_message = model.get('error_message', None)
        description = model.get('description', None)

        # Controlla che la chiave non sia vuota prima di generare gli URL presignati
        thumbnail_url = repository_service.generate_presigned_url_download(thumbnail_s3_key) if thumbnail_s3_key else None
        output_url = repository_service.generate_presigned_url_download(output_s3_key) if output_s3_key else None
        # Restituisci un oggetto del tipo ModelResponse

        # Estrai i risultati se esistono, altrimenti metti None
        results = model.get('results', None)
        
        return ModelResponse(
            _id=model['_id'],
            video_s3_key=model['video_s3_key'],
            thumbnail_url=thumbnail_url,  # sostituisci con presigned URL
            thumbnail_s3_key='',  # sostituisci con presigned URL
            title=model['title'],
            description=description,
            engine=model['engine'],
            output_url=output_url,  # sostituisci con presigned URL
            error_message = error_message,
            output_s3_key='',
            status=model['status'],
            created_at=model['created_at'],
            updated_at=model['updated_at'],
            results=results,
        )

    def list_models_from_db(self,
        page: int,
        limit: int,
        sort_by: Optional[str],
        order: Optional[str],
        title_filter: Optional[str] = None,  # Filtro per title
        status_filter: Optional[List[str]] = None  # Filtro per status
    ) -> Tuple[List[ModelResponse], int]:  # Ora restituisce anche il totale

        # Imposta il campo di ordinamento
        sort_field = "title" if sort_by == "title" else "status" if sort_by == "status" else "created_at"
        sort_order = ASCENDING if order == "asc" else DESCENDING

        # Calcola l'offset per la paginazione
        skip = (page - 1) * limit

        # Costruisci i filtri di ricerca
        filters = {}
        if title_filter:
            filters["title"] = {"$regex": title_filter, "$options": "i"}  # LIKE case-insensitive
        if status_filter:
            filters["status"] = {"$in": status_filter}  # Filtro OR su status

        # Conta il numero totale di modelli che soddisfano il filtro
        total_count = self.db['models'].count_documents(filters)

        # Query per ottenere i modelli con filtri, paginazione e ordinamento
        models_cursor = self.db['models'].find(filters).sort(sort_field, sort_order).skip(skip).limit(limit)

        print('READ MODELS')
        models = []
        for model in models_cursor:
            thumbnail_s3_key = model.get('thumbnail_s3_key', None)
            output_s3_key = model.get('output_s3_key', None)
            error_message = model.get('error_message', None)
            description = model.get('description', None)
            # Controlla che la chiave non sia vuota prima di generare gli URL presignati
            thumbnail_url = repository_service.generate_presigned_url_download(thumbnail_s3_key) if thumbnail_s3_key else None
            output_url = repository_service.generate_presigned_url_download(output_s3_key) if output_s3_key else None

             # Estrai i risultati se esistono, altrimenti metti None
            results = model.get('results', None)
            print('URL SETTED')

            models.append(ModelResponse(
                _id=str(model['_id']),
                video_s3_key=model['video_s3_key'],
                thumbnail_url=thumbnail_url,  # sostituisci con presigned URL
                title=model['title'],
                description=description,
                output_url=output_url,  # sostituisci con presigned URL
                status=model['status'],
                engine=model['engine'],
                error_message=error_message,
                created_at=model['created_at'],
                updated_at=model['updated_at'],
                results=results
            ))

            print('RESPONSE BUILT')

        return models, total_count

