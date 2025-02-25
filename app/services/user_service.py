from app.models.user import UserInDB
from app.config.db import users_collection
from passlib.context import CryptContext
from bson import ObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Funzione per hashare la password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Funzione per verificare la password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Creare un nuovo utente
def create_user(username: str, password: str, role: str = "user"):
    hashed_password = hash_password(password)
    user = UserInDB(username=username, hashed_password=hashed_password, role=role)
    result = users_collection.insert_one(user.dict())
    return str(result.inserted_id)

# Recuperare un utente dal database
def get_user(username: str):
    user = users_collection.find_one({"username": username})
    if user:
        return UserInDB(**user)
    return None
