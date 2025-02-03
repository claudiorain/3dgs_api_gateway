from uuid import uuid4
from uuid import UUID
from datetime import datetime
from app.config.db import get_database  # Assicurati che questa funzione restituisca il client del database
from app.models.model import ModelResponse  # Assumendo che il tuo modello sia in models.py

# Configurazione MongoDB

# Esempio di connessione al DB

# Funzione per creare un modello nel DB
async def create_model_in_db(request):

    db = get_database()  # Ottieni il database con il client asincrono
    model_id = str(uuid4())
    current_time = datetime.utcnow()

    # Documento da inserire in MongoDB
    model_data = {
        "_id": model_id,
        "video_url": request.video_url,
        "model_name": request.model_name,
        "model_folder_url": "",  # Vuoto per ora
        "status": "QUEUED",
        "created_at": current_time,
        "updated_at": current_time
    }

    try:
        result = db["models"].insert_one(model_data)
        print(f"Inserted document ID: {result.inserted_id}")
        return model_data
    except Exception as e:
        print(f"Error inserting document: {e}")
        raise

async def get_model_by_id(model_id: UUID) -> ModelResponse:
    """
    Recupera un modello dal database usando l'ID.
    """
    db = get_database()  # Ottieni il database con il client asincrono
    # Supponiamo che tu abbia una collezione 'models' nel tuo database MongoDB
    model = db['models'].find_one({"_id": str(model_id)})
    
    # Se il modello non esiste
    if model is None:
        return None

    # Restituisci un oggetto del tipo ModelResponse
    return ModelResponse(
        _id=model['_id'],
        video_url=model['video_url'],
        model_name=model['model_name'],
        model_folder_url=model['model_folder_url'],
        status=model['status'],
        created_at=model['created_at'],
        updated_at=model['updated_at']
    )