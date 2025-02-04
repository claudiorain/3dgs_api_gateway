import pika
import json
import os

class QueueJobService:
    def __init__(self, rabbitmq_uri=None):
        # Usa il valore di ambiente RABBITMQ_URI o una URL di default
        self.rabbitmq_uri = rabbitmq_uri or os.getenv('RABBITMQ_URI', 'amqp://rabbitmq:5672')
        self.connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_uri))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='jobs', durable=True)  # Assicuriamoci che la coda 'jobs' esista
        print("Connected to RabbitMQ and queue 'jobs' declared.")
    
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
            routing_key='jobs',  # La coda a cui inviare
            body=message,  # Il messaggio da inviare
            properties=pika.BasicProperties(
                delivery_mode=2,  # Rendere il messaggio persistente
            )
        )

        print(f"Job message for model_id {model_id} sent to queue 'jobs'.")

    def close(self):
        self.connection.close()
