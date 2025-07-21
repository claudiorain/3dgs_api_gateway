# app/models/model.py
from pydantic import BaseModel, HttpUrl,Field,validator
from datetime import datetime
from typing import List,Optional,Dict
from enum import Enum

class PhaseStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class Phase(str,Enum):
    FRAME_EXTRACTION = "frame_extraction"
    POINT_CLOUD_BUILDING = "point_cloud_building"
    DEPTH_REGULARIZATION = "depth_regularization"
    TRAINING = "training"
    UPLOAD = "upload"
    METRICS = "metrics_evaluation"

class Engine(Enum):
    INRIA = "INRIA"
    MCMC = "MCMC" 
    TAMING = "TAMING"



# Mappa fase -> coda
PHASE_TO_QUEUE = {
    Phase.FRAME_EXTRACTION: "frame_extraction_queue",
    Phase.POINT_CLOUD_BUILDING: "point_cloud_queue",
    Phase.DEPTH_REGULARIZATION: "depth_regularization_queue",
    Phase.TRAINING: "model_training_queue",
    Phase.UPLOAD: "upload_queue",
    Phase.METRICS: "metrics_generation_queue"
}

# Mappa inversa coda -> fase
QUEUE_TO_PHASE = {v: k for k, v in PHASE_TO_QUEUE.items()}

class PhaseResult(BaseModel):  # ← Resta qui
    status: PhaseStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None
    
class ModelResponse(BaseModel):
    id: str = Field(alias='_id')
    video_s3_key: str
    model_s3_key: Optional[str] = None  
    thumbnail_url: Optional[str] = None
    thumbnail_suffix: Optional[str] = None
    zip_model_url:Optional[str] = None
    parent_model_id: Optional[str] = None
    # Solo quello che serve davvero
    title: str
    description: Optional[str] = None
    training_config: Optional[Dict] = None
    # Status delle fasi (questo è tutto quello che serve)
    phases: Dict[str, PhaseResult] = {}
    current_phase: Optional[str] = None
    overall_status: PhaseStatus

    created_at: datetime
    updated_at: Optional[datetime] = None
    

class PaginatedModelResponse(BaseModel):
    models: List[ModelResponse]
    totalCount: int
    totalPages: int
    page: int

# Modello dati
class ModelCreateRequest(BaseModel):
    video_s3_key:  Optional[str] = None
    parent_model_id: Optional[str] = None
    title: str
    description: str
    engine: str
    quality_level: str
    from_phase:  Optional[str] = None

    @validator('parent_model_id')
    def validate_mutually_exclusive(cls, v, values):
        video_s3_key = values.get('video_s3_key')
        if v and video_s3_key:
            raise ValueError('video_s3_key and parent_model_id are mutually exclusive')
        if not v and not video_s3_key:
            raise ValueError('Either video_s3_key or parent_model_id must be provided')
        return v
    
    @validator('from_phase')
    def validate_from_phase_logic(cls, v, values):
        video_s3_key = values.get('video_s3_key')
        parent_model_id = values.get('parent_model_id')
        
        if video_s3_key and v is not None:
            raise ValueError('from_phase not allowed for new videos (always starts from frame_extraction)')
        
        if parent_model_id and v is None:
            raise ValueError('from_phase required when forking from parent_model_id')
            
        return v
    
    class Config:
        # Imposta come serializzare HttpUrl
        json_encoders = {
            HttpUrl: lambda v: str(v)  # Converti il tipo HttpUrl in stringa
        }

class PresignedUrlRequest(BaseModel):
    filename: str  # Nome del file che si vuole caricare
    content_type: str  # Tipo di contenuto (es. "image/png", "application/pdf")

