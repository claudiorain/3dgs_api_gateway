from config.s3 import get_client
import os
from botocore.exceptions import NoCredentialsError

S3_BUCKET = os.getenv("AWS_S3_BUCKET")
CACHE_DIR = "/app/cache_s3"  # 📌 Directory locale per la cache

class RepositoryService:
    def __init__(self):
        self.client = get_client()
        os.makedirs(CACHE_DIR, exist_ok=True)  # 📌 Assicuriamoci che la cartella di cache esista

    def get_cache_path(self, s3_key):
        """ Restituisce il percorso locale nella cache per un dato file """
        return os.path.join(CACHE_DIR, s3_key.replace("/", "_"))

    def download(self, s3_key, local_path):
        """ Scarica un file da S3 solo se non è già presente in cache """
        cache_path = self.get_cache_path(s3_key)

        if os.path.exists(cache_path):
            print(f"✅ Usando il file in cache: {cache_path}")
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            os.system(f"cp {cache_path} {local_path}")  # Copia il file dalla cache
        else:
            print(f"⬇️ Scaricamento del file {s3_key} da S3...")
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.client.download_file(S3_BUCKET, s3_key, local_path)
            os.system(f"cp {local_path} {cache_path}")  # Salva

    def generate_presigned_url_upload(self, s3_key, content_type, expiration=3600):
        """
        Genera un Presigned URL per l'upload di un file su S3.
        """
        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={"Bucket": S3_BUCKET, "Key": s3_key, "ContentType": content_type},
                ExpiresIn=expiration,
            )
            return url
        except NoCredentialsError:
            raise Exception("Credenziali AWS mancanti o non valide.") 

    def generate_presigned_url_download(self, s3_key, expiration=3600):
        """
        Genera un Presigned URL per il download di un file da S3.
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url
        except NoCredentialsError:
            raise Exception("Credenziali AWS mancanti o non valide.")