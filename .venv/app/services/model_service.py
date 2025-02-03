from uuid import uuid4
from datetime import datetime
from pymongo import MongoClient
from pydantic import HttpUrl

# Configurazione MongoDB
client = MongoClient('mongodb://mongo:27017/')
db = client["mydatabase"]
collection = db["models"]


# Funzione per creare un modello nel DB
async def create_model_in_db(request):
    model_id = uuid4()
    current_time = datetime.utcnow()

    # Documento da inserire in MongoDB
    model_data = {
        "_id": str(model_id),
        "video_url": request.video_url,
        "model_name": request.model_name,
        "model_folder_url": "",  # Vuoto per ora
        "status": "QUEUED",
        "created_at": current_time,
        "updated_at": current_time
    }

    # Inserisci nel DB
    collection.insert_one(model_data)

    # Ritorna il modello creato
    return {
        "id": model_id,
        "video_url": request.video_url,
        "model_name": request.model_name,
        "model_folder_url": "",
        "status": "QUEUED",
        "created_at": current_time,
        "updated_at": current_time
    }