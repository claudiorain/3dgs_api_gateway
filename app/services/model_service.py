from uuid import uuid4
from uuid import UUID
from datetime import datetime
from app.config.db import get_database  # Assicurati che questa funzione restituisca il client del database
from app.models.model import ModelResponse  # Assumendo che il tuo modello sia in models.py
from typing import List, Optional, Tuple
from pymongo import ASCENDING, DESCENDING
from app.models.model import ModelCreateRequest  # Assumendo che il tuo modello sia in models.py
from app.services.repository_service import RepositoryService
from app.models.model import Phase,PhaseStatus  # Assumendo che il tuo modello sia in models.py
import os
import mimetypes

# Configurazione MongoDB
S3_STAGING_PREFIX = os.getenv('S3_STAGING_PREFIX', 'staging')

# Cartella per i deliverable finali
S3_DELIVERY_PREFIX = os.getenv('S3_DELIVERY_PREFIX', 'delivery')

repository_service = RepositoryService()
# ✅ MIME ammessi (aggiunto lo zip)

# Esempio di connessione al DB
class ModelService:

    def __init__(self):
        """Inizializza la connessione a MongoDB."""
        self.db = get_database()  # Ottieni il database con il client asincrono

    def _validate_fork_prerequisites(self, parent_project: ModelResponse, from_phase_str: str):
        """Valida che il parent abbia completato le fasi prerequisite"""
        phase_order = [Phase.FRAME_EXTRACTION, Phase.POINT_CLOUD_BUILDING, 
                       Phase.TRAINING]
        
        from_phase = Phase(from_phase_str)  # Converte "frame_extraction" in Phase.FRAME_EXTRACTION

        if from_phase not in phase_order:
            raise ValueError(f"Invalid from_phase: {from_phase_str}")
        
        from_phase_idx = phase_order.index(from_phase)
        
        # Verifica che tutte le fasi precedenti siano completate
        for i in range(from_phase_idx):
            required_phase = phase_order[i]
            print(f"📋 Phases: {parent_project.phases}")

            if required_phase not in parent_project.phases:
                raise ValueError(f"Parent project missing required phase: {required_phase}")
            
            phase_status = parent_project.phases[required_phase].status
            if phase_status not in [PhaseStatus.COMPLETED, PhaseStatus.FAILED]:
                raise ValueError(
                    f"Parent project must have completed {required_phase} "
                    f"before forking from {from_phase_str}. Current status: {phase_status}"
                )
    # Funzione per creare un modello nel DB
    async def create_model_in_db(self, request: ModelCreateRequest) -> ModelResponse:

        model_id = str(uuid4())
        current_time = datetime.utcnow()
        model_s3_key = f"models/{model_id}/"
        if request.video_s3_key:
        # Documento da inserire in MongoDB
            model_data = {
                "_id": model_id,
                "model_s3_key": model_s3_key,
                "video_s3_key": request.video_s3_key,
                "thumbnail_suffix": None,
                "parent_model_id": None,
                "title": request.title,
                "description": request.description,
                "training_config": {
                    "engine": request.engine,
                    "quality_level":request.quality_level
                },
                "phases": {
                    "frame_extraction": {
                        "status": "PENDING",
                        "started_at": None,
                        "completed_at": None,
                        "error_message": None,
                        "metadata": None
                    }
                },
                "overall_status": "PENDING",
                "current_phase": "frame_extraction",
                "created_at": current_time,
                "updated_at": current_time
            }
        elif request.parent_model_id:
            # 1. Leggi progetto parent tramite servizio
            try:
                parent_model = self.get_model_by_id(UUID(request.parent_model_id))
            except Exception as e:
                raise ValueError(f"Parent project {request.parent_model_id} not found: {e}")
        
            # 2. Valida che la fase from sia disponibile nel parent
            current_phase = request.from_phase
            self._validate_fork_prerequisites(parent_model, current_phase)

            

            # 4. Determina fasi da copiare (fino a from_phase esclusa)
            phase_order = ["frame_extraction", "point_cloud_building", "training"]
            until_phase_idx = phase_order.index(current_phase)
            phases_to_copy = phase_order[:until_phase_idx]

            # 5. Copia fasi come SKIPPED
            skipped_phases = {}
            for phase in phases_to_copy:
                phase_str = phase if isinstance(phase, str) else phase.value
                parent_phases_dict = {str(k): v for k, v in parent_model.phases.items()}

                if phase_str in parent_phases_dict:
                    parent_phase = parent_phases_dict[phase_str]
                    skipped_phases[phase_str] = {
                        "status": "SKIPPED",
                        "started_at": parent_phase.started_at,
                        "completed_at": parent_phase.completed_at,
                        "error_message": None,
                        "metadata": parent_phase.metadata,
                    }
        
            
            # 6. Aggiungi fase from come PENDING
            skipped_phases[current_phase] = {
                "status": "PENDING",
                "started_at": None,
                "completed_at": None,
                "error_message": None,
                "metadata": None
            }
            print(f"current_phase: {current_phase}")
            print(f"phases_to_copy: {phases_to_copy}")
            print(f"skipped_phases keys: {list(skipped_phases.keys())}")
            for phase, data in skipped_phases.items():
                print(f"Phase {phase}: status={data['status']}")

            # 7. Crea documento progetto biforcato
            model_data = {
                "_id": model_id,
                "video_s3_key": parent_model.video_s3_key,  # Stesso video
                "model_s3_key": model_s3_key,
                "thumbnail_suffix": parent_model.thumbnail_suffix,  # Stesso thumbnail
                "parent_model_id": request.parent_model_id,
                
                "title": request.title,
                "description": request.description,
                
                "training_config": {
                    "engine": request.engine,
                    "quality_level":request.quality_level
                },
                
                "phases": skipped_phases,
                "overall_status": "PENDING",
                "current_phase": current_phase,
                
                "created_at": current_time,
                "updated_at": current_time
            }

            # 3. Copia cartella modello del parent su S3

            # 🖼️ COPIA SOLO LA THUMBNAIL (i file delle fasi verranno gestiti dai ZIP di staging)
            try:
                await self.copy_thumbnail_for_forked_model(
                    parent_model_id=request.parent_model_id,
                    new_model_id=model_id,
                    thumbnail_suffix=parent_model.thumbnail_suffix
                )
                print(f"✅ Thumbnail copied for forked model {model_id}")
            except Exception as e:
                print(f"⚠️ Warning: Could not copy thumbnail: {e}")
                # Non bloccare la creazione del modello per errori di thumbnail

        try:
            result = self.db["models"].insert_one(model_data)
            print(f"Inserted document ID: {result.inserted_id}")
            return self.get_model_by_id(UUID(model_data["_id"]))
        except Exception as e:
            print(f"Error inserting document: {e}")
            raise

    async def update_model_for_retry(self, model_id: UUID) -> ModelResponse:
        try:
            model = self.get_model_by_id(UUID(model_id))
        except Exception as e:
            raise ValueError(f"Model {model_id} not found: {e}")
        
        # Trova la fase con status FAILED
        interrupted_phase = None
        for phase_name, phase_data in model.phases.items():
            print(phase_data)
            
            # Confronta direttamente con gli enum oppure con le stringhe
            if  phase_data.status in [PhaseStatus.FAILED, PhaseStatus.RUNNING, PhaseStatus.PENDING]:
                interrupted_phase = phase_name
                break
        print(f"1")

        if not interrupted_phase:
            raise ValueError(f"No INTERRUPTED phase found for model {model_id}")
        
        current_time = datetime.utcnow()
    
        # Prepara gli aggiornamenti
        update_data = {
            "overall_status": "PENDING",
            "current_phase": interrupted_phase,
            "updated_at": current_time,
            f"phases.{interrupted_phase}.status": "PENDING",
            f"phases.{interrupted_phase}.started_at": None,
            f"phases.{interrupted_phase}.completed_at": None,
            f"phases.{interrupted_phase}.error_message": None
        }

        print(f"2")

        try:
            # Aggiorna il documento in MongoDB
            result = self.db["models"].update_one(
                {"_id": str(model_id)},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise ValueError(f"Model {model_id} not found in database")
            
            print(f"✅ Model {model_id} updated for retry. Phase {interrupted_phase} reset to PENDING")
            print(f"5")

            # Ritorna il modello aggiornato
            return self.get_model_by_id(UUID(model_id))
        
        except Exception as e:
            print(f"❌ Error updating model for retry: {e}")
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

        thumbnail_url = self.get_thumbnail_url_if_exist(model)
        zip_model_url = self.get_zip_model_url_if_exist(model)

        # Restituisci un oggetto del tipo ModelResponse        
        return ModelResponse(
                _id=str(model['_id']),
                video_s3_key=model.get('video_s3_key', None),
                model_s3_key=model.get('model_s3_key', None),
                thumbnail_url=thumbnail_url,
                thumbnail_suffix=model.get('thumbnail_suffix', None),
                parent_model_id=model.get('parent_model_id', None),
                
                title=model['title'],
                description=model.get('description', None),
                zip_model_url=zip_model_url,
                # Campi legacy (se esistono)
                
                # Nuova struttura
                training_config=model.get('training_config'),
                phases=model.get('phases', {}),
                overall_status=model.get('overall_status', 'PENDING'),
                current_phase=model.get('current_phase'),
                
                created_at=model['created_at'],
                updated_at=model.get('updated_at')
            )

    def list_models_from_db(self,
        page: int,
        limit: int,
        sort_by: Optional[str],
        order: Optional[str],
        title_filter: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        engine_filter: Optional[List[str]] = None
    ) -> Tuple[List[ModelResponse], int]:
    
        # Imposta il campo di ordinamento
        sort_field = "title" if sort_by == "title" else "status" if sort_by == "status" else "created_at"
        sort_order = ASCENDING if order == "asc" else DESCENDING
        
        # Calcola l'offset per la paginazione
        skip = (page - 1) * limit
        
        # Costruisci i filtri di ricerca
        filters = {}
        if title_filter:
            filters["title"] = {"$regex": title_filter, "$options": "i"}
        if status_filter:
            filters["overall_status"] = {"$in": status_filter}
        if engine_filter:
            filters["training_config.engine"] = {"$in": engine_filter}
        
        # Conta il numero totale di modelli
        total_count = self.db['models'].count_documents(filters)
        
        # Query per ottenere i modelli
        models_cursor = self.db['models'].find(filters).sort(sort_field, sort_order).skip(skip).limit(limit)
        
        print('READ MODELS')
        models = []
        for model in models_cursor:
            thumbnail_url = self.get_thumbnail_url_if_exist(model)
            zip_model_url = self.get_zip_model_url_if_exist(model)

                # Mappa direttamente tutti i campi dal DB
            models.append(ModelResponse(
                _id=str(model['_id']),
                video_s3_key=model.get('video_s3_key', None),
                model_s3_key=model.get('model_s3_key', None),
                thumbnail_url=thumbnail_url,
                parent_model_id=model.get('parent_model_id', None),
                
                title=model['title'],
                description=model.get('description', None),
                zip_model_url=zip_model_url,
                
                # Nuova struttura
                training_config=model.get('training_config'),
                phases=model.get('phases', {}),
                overall_status=model.get('overall_status', 'PENDING'),
                current_phase=model.get('current_phase'),
                
                created_at=model['created_at'],
                updated_at=model.get('updated_at')
            ))
        return models, total_count

    async def copy_thumbnail_for_forked_model(self, parent_model_id: str, new_model_id: str,thumbnail_suffix: str):
        """
        Copia solo la thumbnail dal parent model al nuovo model in delivery.
        
        Args:
            parent_model_id: ID del modello parent
            new_model_id: ID del nuovo modello biforcato
        """
        try:
            # Costruisci i percorsi S3 usando le costanti standardizzate
            parent_thumbnail_s3_key = f"{S3_DELIVERY_PREFIX}/{parent_model_id}/{thumbnail_suffix}"
            new_thumbnail_s3_key = f"{S3_DELIVERY_PREFIX}/{new_model_id}/{thumbnail_suffix}"
            
            print(f"📸 Copying thumbnail:")
            print(f"  From: {parent_thumbnail_s3_key}")
            print(f"  To: {new_thumbnail_s3_key}")
            
            print(f"📸 Copying thumbnail:")
            print(f"  From: {parent_thumbnail_s3_key}")
            print(f"  To: {new_thumbnail_s3_key}")
            
            # Prova a copiare la thumbnail - se non esiste verrà catturato nell'except
            await repository_service.copy_s3_file(parent_thumbnail_s3_key, new_thumbnail_s3_key)
            print(f"✅ Thumbnail copied successfully")
                
        except Exception as e:
            print(f"⚠️ Could not copy thumbnail (probably doesn't exist): {e}")
            # Non rilanciare l'errore - la thumbnail è opzionale
                
        except Exception as e:
            print(f"❌ Error copying thumbnail: {e}")
            raise

    def _should_thumbnail_exist(self, phases):
        """
        Verifica se la thumbnail dovrebbe esistere in base alle fasi completate.
        """
        frame_extraction = phases.get('frame_extraction', {})
        return frame_extraction.get('status') in ['COMPLETED','SKIPPED']
    def _should_model_zip_exist(self, overall_status):
        """
        Verifica se il ZIP del modello dovrebbe esistere.
        """
        # ZIP finale disponibile solo quando tutto è completato
        return overall_status == 'COMPLETED'

    def get_zip_model_url_if_exist(self, model):
        zip_model_url  = None
        if self._should_model_zip_exist(model.get('overall_status')):
            zip_model_suffix = model.get('zip_model_suffix')
            if zip_model_suffix:
                zip_model_s3_key = f"{S3_DELIVERY_PREFIX}/{model['_id']}/{zip_model_suffix}"
                zip_model_url = repository_service.generate_presigned_url_download(zip_model_s3_key)
        
        return zip_model_url
    
    def get_thumbnail_url_if_exist(self, model):
        thumbnail_url  = None
        if self._should_thumbnail_exist(model.get('phases')) and model.get('thumbnail_suffix',None) != None:
            thumbnail_suffix = model.get('thumbnail_suffix')
            if thumbnail_suffix:
                thumbnail_s3_key = f"{S3_DELIVERY_PREFIX}/{model['_id']}/{thumbnail_suffix}"
                thumbnail_url = repository_service.generate_presigned_url_download(thumbnail_s3_key)
        return thumbnail_url
    
