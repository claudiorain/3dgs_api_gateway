# Usa una base image ufficiale di Python
FROM python:3.10

# Crea e imposta la working directory
WORKDIR /app

# Copia il progetto locale nella working directory del container
COPY . /app/

# Crea e attiva l'ambiente virtuale nella directory .venv
RUN python -m venv .venv

# Imposta il PATH per utilizzare l'ambiente virtuale
ENV PATH="/app/.venv/bin:$PATH"

# Installa le dipendenze nell'ambiente virtuale
RUN pip install --no-cache-dir -r requirements.txt

# Espone la porta dell'API
EXPOSE 8000

# Comando per avviare l'app FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
