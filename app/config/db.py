from pymongo import MongoClient,ASCENDING
import os


# Funzione per ottenere il client del database
def get_database():
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongo:27017"))
    return client.get_database()  # Restituisce direttamente il database

database = get_database()
users_collection = database["users"]

# Creiamo un indice unico su `username`
def init_db():
    users_collection.create_index([("username", ASCENDING)], unique=True)


