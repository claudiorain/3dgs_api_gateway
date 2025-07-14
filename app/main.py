from http.client import HTTPException
from typing import List, Optional,Set
from passlib.context import CryptContext
from fastapi import FastAPI, Depends, HTTPException, Security,Query,status,WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm,HTTPBasic, HTTPBasicCredentials
import secrets  # Per confrontare le password in modo sicuro
import os
import json
from app.config.db import add_change_listener
from uuid import UUID, uuid4
from datetime import datetime,timedelta
import jwt
from app.services.model_service import ModelService
from app.services.queue_job_service import QueueJobService
from app.services.repository_service import RepositoryService
from app.models.model import ModelResponse  # Assumendo che il tuo modello sia in models.py
from app.models.model import PaginatedModelResponse  # Assumendo che il tuo modello sia in models.py
from app.models.model import ModelCreateRequest  # Assumendo che il tuo modello sia in models.py
from app.models.model import PresignedUrlRequest  # Assumendo che il tuo modello sia in models.py
from app.models.user import UserInDB
from app.models.user import UserRegistration
from app.services.user_service import get_user
from app.services.user_service import create_user
from app.config.db import init_db
from app.utils.notification_utils import process_and_send_notification

# Cartella principale per i video sorgente
S3_VIDEOS_PREFIX = os.getenv('S3_VIDEOS_PREFIX', 'videos/')

# Secret Key per JWT
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBasic()
# Connessioni WebSocket attive
active_connections: Set[WebSocket] = set()

def verify_basic_auth(credentials: HTTPBasicCredentials = Security(security)):
    valid_username = "admin"
    valid_password = "supersecret"

    is_valid_username = secrets.compare_digest(credentials.username, valid_username)
    is_valid_password = secrets.compare_digest(credentials.password, valid_password)

    if not (is_valid_username and is_valid_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return credentials.username  # Utente autenticato

app = FastAPI()  # 🔥 Protegge TUTTE le API

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Configura Basic Authentication

# OAuth2 Bearer token per autenticazione
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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

def verify_password(plain_password, hashed_password):
    print('plain: ' +plain_password )
    print('hashed: ' +hashed_password )
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/register")
async def register_user(user: UserRegistration,dependencies=[Depends(verify_basic_auth)]):
    existing_user =  get_user(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    user_id = create_user(user.username, user.password, user.role)
    return {"message": "User created successfully", "user_id": user_id}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)  # Recupera da MongoDB
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/protected")
def protected_route(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"message": f"Welcome, {username}!"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
# 1️⃣ Endpoint per creare un nuovo modello
@app.post("/models/", response_model=ModelResponse,dependencies=[Depends(verify_basic_auth)])
async def create_model(request: ModelCreateRequest):
     try:
        # Chiama il servizio per creare il modello in MongoDB
        model = await model_service.create_model_in_db(request)
        # Invia il job a RabbitMQ
        queue_job_service.send_job(model.id,model.current_phase)
        return model
     except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
     
@app.post("/models/{model_id}/retry", response_model=ModelResponse, dependencies=[Depends(verify_basic_auth)])
async def retry_model(model_id: str):
    try:
        # Recupera il modello esistente dal database
        model = await model_service.update_model_for_retry(model_id)
        
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        queue_job_service.send_job(model.id, model.current_phase)
        
        return model
        
    except HTTPException:
        # Re-raise HTTP exceptions (come 404)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2️⃣ Endpoint per ottenere la lista dei modelli con paginazione e sorting
@app.get("/models/", response_model=PaginatedModelResponse,dependencies=[Depends(verify_basic_auth)])
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
    print('Searching models')
    try:
        models, total_count = model_service.list_models_from_db(
            page, limit, sort_by, order, title_filter=title, status_filter=status
        )
        
        print('RESPONSE BUILT')
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
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))


# 3️⃣ Endpoint per eliminare un modello tramite ID
@app.delete("/models/{model_id}", response_model=dict,dependencies=[Depends(verify_basic_auth)])
async def delete_model(model_id: UUID):
    """
    Elimina un modello dal database.
    """
    pass  # Implementazione futura

@app.get("/models/{model_id}", response_model=ModelResponse,dependencies=[Depends(verify_basic_auth)])
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
@app.post("/s3/upload-url/",dependencies=[Depends(verify_basic_auth)])
async def get_upload_url(request: PresignedUrlRequest):
    """
    Genera un UUID per il modello e restituisce un URL presigned per l'upload.
    Il file verrà caricato dentro una cartella con il nome dell'UUID.
    """
    # 1️⃣ Genera UUID per la cartella del modello
    upload_id = str(uuid4())
    s3_key = f"{S3_VIDEOS_PREFIX}/{upload_id}/{request.filename}"  # File all'interno della cartella

    try:
        presigned_url = repository_service.generate_presigned_url_upload(
            s3_key,request.content_type
        )
       
        response = {"upload_id": upload_id, "upload_url": presigned_url,"video_s3_key": s3_key}
        # Logga la risposta
        print(f"RESPONSE: {response}")

        # 3️⃣ Restituisci UUID e URL per l'upload
        return response
    except Exception as e:
        print(f"ERRORE: {str(e)}")
        return {"error": str(e)}


async def notify_clients(change_data: dict):
    """Processore principale delle notifiche - ora super pulito!"""
    await process_and_send_notification(change_data, active_connections)

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """Endpoint WebSocket per ricevere notifiche real-time"""
    await websocket.accept()
    active_connections.add(websocket)
    
    print(f"Client connected. Total connections: {len(active_connections)}")
    
    try:
        # Mantieni la connessione attiva con heartbeat
        while True:
            data = await websocket.receive_text()
            # Opzionale: gestisci messaggi dal client (ping/pong)
            if data == "ping":
                await websocket.send_text("pong")
    except Exception as e:
        print(f"WebSocket connection error: {e}")
    finally:
        active_connections.discard(websocket)
        print(f"Client disconnected. Total connections: {len(active_connections)}")

@app.on_event("startup")
async def startup_db():
    init_db()
    # Registra il listener per le notifiche
    add_change_listener(notify_clients)
    print("Notification system initialized")        
    
@app.get("/health")
async def health_check():
    return {"status": "success", "message": "API is up and running!"}
