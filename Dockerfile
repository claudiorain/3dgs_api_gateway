# Fase 1: Costruzione dell'applicazione FastAPI
FROM python:3.9 AS api-gateway-builder

WORKDIR /code

# Copia i file di requirements e installa le dipendenze
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copia il codice dell'applicazione FastAPI
COPY ./app /code/app

# ESPONE la porta 8000 per FastAPI
EXPOSE 8000

# Fase 2: Setup di Nginx come reverse proxy
FROM nginx:alpine

# Copia la configurazione di Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Copia i file dell'applicazione FastAPI dalla build precedente
COPY --from=api-gateway-builder /code /code

# ESPONE la porta 8000 per FastAPI attraverso Nginx
EXPOSE 8000

# Avvia il reverse proxy Nginx e il server FastAPI
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 & nginx -g 'daemon off;'"]
