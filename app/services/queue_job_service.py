import pika
import json
import os
from app.config.message_queue import get_connection  # Assicurati che questa funzione restituisca il client del database
from app.config.message_queue import get_channel  # Assicurati che questa funzione restituisca il client del database

class QueueJobService:

    def __init__(self):
        """Inizializza la connessione a RabbitMQ (può rimanere None finché non serve)."""
        self.connection = get_connection()
        self.channel = get_channel(self.connection)

    def create_job_message(self, model_id: str):
        # Crea un messaggio con l'id del modello
        job_message = {
            'model_id': model_id,
            'task': 'process_model',  # Puoi aggiungere altre informazioni necessarie
        }

        # Converte il messaggio in formato JSON
        return json.dumps(job_message)
    
    def send_job(self, model_id: str):
        # Crea un messaggio di lavoro con l'ID del modello
        message = self.create_job_message(model_id)
        
        # Invia il messaggio alla coda
        self.channel.basic_publish(
            exchange='',  # Default exchange
            routing_key='3dgs',  # La coda a cui inviare
            body=message,  # Il messaggio da inviare
            properties=pika.BasicProperties(
                delivery_mode=2,  # Rendere il messaggio persistente
            )
        )

        print(f"Job message for model_id {model_id} sent to queue '3dgs'.")

        

    def handle_exit(self, signum, frame):
        """Gestisce la chiusura dell'applicazione"""
        print("\n🛑 Closing application...")
        close_connection(self.connection)
        sys.exit(0)
