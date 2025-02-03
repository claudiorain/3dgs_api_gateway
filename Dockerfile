# Usa una base image ufficiale di Python
FROM python:3.10

# Crea e imposta la working directory
WORKDIR /app

# Crea la directory .venv/app
RUN mkdir -p .venv

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Espone la porta dell'API
EXPOSE 8000

# Comando per avviare l'app FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]