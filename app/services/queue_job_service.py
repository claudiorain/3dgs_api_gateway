import pika
import json
import sys
from app.config.message_queue import get_connection  # Assicurati che questa funzione restituisca il client del database
from app.config.message_queue import get_channel  # Assicurati che questa funzione restituisca il client del database
from app.models.model import Phase

# Mappa fase -> coda
PHASE_TO_QUEUE = {
    Phase.FRAME_EXTRACTION: "frame_extraction_queue",
    Phase.POINT_CLOUD_BUILDING: "point_cloud_queue",
    Phase.DEPTH_REGULARIZATION: "depth_regularization_queue",
    Phase.TRAINING: "model_training_queue",
    Phase.UPLOAD: "upload_queue",
    Phase.METRICS: "metrics_generation_queue"
}

# Mappa inversa coda -> fase (utile per il consumer)
QUEUE_TO_PHASE = {v: k for k, v in PHASE_TO_QUEUE.items()}

class QueueJobService:

    def __init__(self):
        """Inizializza la connessione a RabbitMQ."""
        self.connection = get_connection()
        self.channel = get_channel(self.connection)

    def create_job_message(self, model_id: str, additional_data=None):
        """
        Crea un messaggio con l'ID del modello e eventuali dati aggiuntivi.
        """
        job_message = {'model_id': model_id}
        
        if additional_data:
            job_message.update(additional_data)
        
        # Converte il messaggio in formato JSON
        return json.dumps(job_message)

    def send_job(self, model_id: str, phase_str: str, additional_data=None):
        """
        Invia un messaggio alla coda specificata (che rappresenta una fase del job).
        """

        try:
            phase = Phase(phase_str)
        except ValueError:
            raise ValueError(f"Invalid phase: {phase_str}")
        
         # Mappa la fase alla coda
        queue_name = PHASE_TO_QUEUE.get(phase)
        if not queue_name:
            raise ValueError(f"No queue mapped for phase: {phase}")

        message = self.create_job_message(model_id, additional_data)

        # Invia il messaggio alla coda corretta
        self.channel.basic_publish(
            exchange='',  # Default exchange
            routing_key=queue_name,  # Coda specifica della fase
            body=message,  # Il messaggio da inviare
            properties=pika.BasicProperties(
                delivery_mode=2,  # Rendere il messaggio persistente
            )
        )

        print(f"Job message for model_id {model_id} sent to queue '{queue_name}'.")

    def handle_exit(self, signum, frame):
        """Gestisce la chiusura dell'applicazione"""
        print("\n🛑 Closing application...")
        self.close_connection(self.connection)
        sys.exit(0)
