"""
Utilities per gestire le notifiche WebSocket ai client
"""
import json
import copy
from datetime import datetime
from typing import Dict, List, Optional, Any

class NotificationAnalyzer:
    """Analizza i change events di MongoDB e determina le notifiche utili"""
    
    PHASE_DISPLAY_NAMES = {
        "frame_extraction": "Frame Extraction",
        "colmap": "3D Reconstruction",
        "training": "Model Training", 
        "upload": "Upload & Finalization",
        "metrics_evaluation": "Quality Assessment"
    }
    
    STATUS_DISPLAY_NAMES = {
        "PENDING": "Pending",
        "RUNNING": "In Progress",
        "COMPLETED": "Completed", 
        "FAILED": "Failed",
        "CANCELLED": "Cancelled"
    }
    
    @classmethod
    def determine_notification_type(cls, change_data: dict) -> dict:
        """Determina se il cambiamento è utile per il frontend"""
        
        if change_data.get("operationType") == "insert":
            return {
                "type": "model_created",
                "useful": True
            }
        
        if change_data.get("operationType") == "update":
            updated_fields = change_data.get('updateDescription', {}).get('updatedFields', {})
            
            for field, value in updated_fields.items():
                
                # Cambio status globale
                if field == 'overall_status':
                    return {
                        "type": "model_status_changed",
                        "new_status": value,
                        "useful": True
                    }
                
                # Cambio status di una fase
                elif field.startswith('phases.') and field.endswith('.status'):
                    phase_name = field.split('.')[1]
                    
                    if value == "RUNNING":
                        notification_type = "phase_started"
                    elif value == "COMPLETED":
                        notification_type = "phase_completed"
                    elif value == "FAILED":
                        notification_type = "phase_failed"
                    else:
                        continue  # Ignora altri status
                    
                    return {
                        "type": notification_type,
                        "phase": phase_name,
                        "new_status": value,
                        "useful": True
                    }
        
        # Ignora tutti gli altri cambiamenti
        return {"useful": False}
    
    @classmethod
    def extract_model_info(cls, full_document: dict) -> dict:
        """Estrae informazioni utili del modello per l'utente"""
        if not full_document:
            return {}
        
        return {
            "title": full_document.get("title", "Unknown Model"),
            "description": full_document.get("description"),
            "overall_status": full_document.get("overall_status"),
            "current_phase": full_document.get("current_phase"),
            "created_at": full_document.get("created_at").isoformat() if full_document.get("created_at") else None
        }
    
    @classmethod
    def get_phase_display_name(cls, phase: str) -> str:
        """Converte nome fase tecnico in user-friendly"""
        return cls.PHASE_DISPLAY_NAMES.get(phase, phase.title())
    
    @classmethod
    def get_status_display_name(cls, status: str) -> str:
        """Converte status tecnico in user-friendly"""
        return cls.STATUS_DISPLAY_NAMES.get(status, status.title())


class NotificationBuilder:
    """Costruisce le notifiche per il frontend"""
    
    @staticmethod
    def build_notification(change_data: dict, notification_info: dict) -> dict:
        """Costruisce la notifica completa per il frontend"""
        
        # Estrai dati del modello
        full_document = change_data.get("fullDocument")
        model_info = NotificationAnalyzer.extract_model_info(full_document)
        
        # Notifica base
        notification = {
            "type": notification_info["type"],
            "operation": change_data.get("operationType"),
            "model_id": str(change_data.get("documentKey", {}).get("_id", "")),
            "timestamp": datetime.utcnow().isoformat(),
            "model_title": model_info.get("title")
        }
        
        # Aggiungi dettagli specifici per tipo
        if notification_info["type"] in ["phase_started", "phase_completed", "phase_failed"]:
            # Solo phase e model_title per le notifiche delle fasi
            notification["phase"] = notification_info["phase"]
            
        elif notification_info["type"] == "model_status_changed":
            # Solo overall_status per i cambiamenti globali
            notification["overall_status"] = notification_info["new_status"]
            
        elif notification_info["type"] == "model_created":
            # Dati completi solo per la creazione
            notification.update({
                "model_description": model_info.get("description"),
                "overall_status": model_info.get("overall_status")
            })
        
        return notification
    
    @staticmethod
    def prepare_json_serializable(data: Any) -> Any:
        """Converte oggetti non serializzabili in JSON"""
        if data is None:
            return None
        
        # Crea una copia per non modificare l'originale
        json_data = copy.deepcopy(data)
        
        def convert_item(item):
            if isinstance(item, datetime):
                return item.isoformat()
            elif hasattr(item, '__iter__') and not isinstance(item, (str, bytes)):
                if isinstance(item, dict):
                    return {key: convert_item(value) for key, value in item.items()}
                elif isinstance(item, list):
                    return [convert_item(element) for element in item]
            elif hasattr(item, '__str__') and type(item).__name__ == 'ObjectId':
                return str(item)
            return item
        
        return convert_item(json_data)


class NotificationSender:
    """Gestisce l'invio delle notifiche ai client WebSocket"""
    
    @staticmethod
    async def send_to_clients(notification: dict, active_connections: set) -> None:
        """Invia la notifica a tutti i client connessi"""
        if not active_connections:
            return
        
        model_title = notification.get("model_title", "Unknown")
        notification_type = notification.get("type")
        
        print(f"📤 Sending {notification_type} for '{model_title}' to {len(active_connections)} clients")
        
        # Lista delle connessioni da rimuovere (chiuse)
        disconnected = set()
        
        for websocket in active_connections:
            try:
                await websocket.send_text(json.dumps(notification))
            except Exception as e:
                print(f"❌ Failed to send notification: {e}")
                disconnected.add(websocket)
        
        # Rimuovi le connessioni chiuse
        active_connections.difference_update(disconnected)
        
        if disconnected:
            print(f"🔌 Removed {len(disconnected)} disconnected clients")


# Funzione principale per il main.py
async def process_and_send_notification(change_data: dict, active_connections: set) -> None:
    """Funzione principale per processare e inviare notifiche"""
    
    # 1. Analizza se il cambiamento è utile
    notification_info = NotificationAnalyzer.determine_notification_type(change_data)
    
    if not notification_info.get("useful"):
        print("🔇 Change ignored (not useful for frontend)")
        return
    
    # 2. Costruisci la notifica
    notification = NotificationBuilder.build_notification(change_data, notification_info)
    
    # 3. Invia ai client
    await NotificationSender.send_to_clients(notification, active_connections)