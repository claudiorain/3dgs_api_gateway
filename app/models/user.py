from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    username: str

class UserInDB(BaseModel):
    username: str
    hashed_password: str
    role: Optional[str] = "user"
    created_at: datetime = datetime.utcnow()

class UserRegistration(BaseModel):
    username: str
    password: str
    role: str = "user"