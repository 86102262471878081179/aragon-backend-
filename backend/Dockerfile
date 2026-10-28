FROM python:3.11-slim

# Verhindert, dass Python .pyc-Dateien schreibt und puffert die Logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Kopiere zuerst nur die Requirements, um den Docker-Cache effizient zu nutzen
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den gesamten Rest (inklusive main.py, b6_registry.db, ingest-registry.py, data-Ordner etc.)
COPY . .

EXPOSE 8000

# Starte den FastAPI-Server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
