from app.models.user import UserInDB
from app.config.db import users_collection
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from bson import ObjectId

password_hash = PasswordHash((
    Argon2Hasher(),  # Algoritmo principale per nuove password  
    BcryptHasher(),  # Compatibilità con password bcrypt esistenti
))
# Funzione per hashare la password
def get_password_hash(password):
    """Crea un hash della password usando Argon2 (algoritmo moderno)"""
    return password_hash.hash(password)

# Funzione per verificare la password
def verify_password(plain_password, hashed_password):
    print('plain: ' + plain_password)
    print('hashed: ' + hashed_password)
    return password_hash.verify(plain_password, hashed_password)

# Creare un nuovo utente
def create_user(username: str, password: str, role: str = "user"):
    hashed_password = get_password_hash(password)
    user = UserInDB(username=username, hashed_password=hashed_password, role=role)
    result = users_collection.insert_one(user.dict())
    return str(result.inserted_id)

# Recuperare un utente dal database
def get_user(username: str):
    user = users_collection.find_one({"username": username})
    if user:
        return UserInDB(**user)
    return None
