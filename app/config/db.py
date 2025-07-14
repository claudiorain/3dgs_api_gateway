from pymongo import MongoClient,ASCENDING
from threading import Thread
import asyncio
from typing import List, Callable
import os


# Funzione per ottenere il client del database
def get_database():
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongo:27017"))
    return client.get_database()  # Restituisce direttamente il database

database = get_database()
users_collection = database["users"]
models_collection = database["models"] 

change_listeners: List[Callable] = []

# Creiamo un indice unico su `username`
def init_db():
    users_collection.create_index([("username", ASCENDING)], unique=True)
    # Avvia il monitoring dei change streams in un thread separato
    change_thread = Thread(target=watch_model_changes, daemon=True)
    change_thread.start()
    print("Database initialized and change monitoring started")

def add_change_listener(listener: Callable):
    """Registra un listener per i cambiamenti del database"""
    change_listeners.append(listener)

def watch_model_changes():
    """Monitora i cambiamenti nella collection models"""
    try:
        pipeline = [
            {
                "$match": {
                    "operationType": {"$in": ["insert", "update", "delete"]}
                }
            }
        ]
        
        change_stream = models_collection.watch(
            pipeline, 
            full_document='updateLookup'  
        )
        
        print("🔍 Starting to watch model changes...")
        
        for change in change_stream:
            print(f"📝 Detected change: {change['operationType']}")
            
            # DEBUG temporaneo
            if 'fullDocument' in change and change['fullDocument']:
                print(f"✅ DEBUG: fullDocument title: '{change['fullDocument'].get('title')}'")
            else:
                print("❌ DEBUG: fullDocument missing or empty")
            
            for listener in change_listeners:
                try:
                    asyncio.run(listener(change))
                except Exception as e:
                    print(f"❌ Error in change listener: {e}")
                    
    except Exception as e:
        print(f"❌ Error watching changes: {e}")
