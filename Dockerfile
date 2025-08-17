# Imagen base slim
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependencias del sistema (psycopg2, curl para healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

# Usuario no-root
RUN useradd -m -u 10001 appuser

WORKDIR /app

# Instalar deps de Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar app
COPY app.py /app/app.py

# Permisos
RUN chown -R appuser:appuser /app
USER appuser

# Puerto interno
EXPOSE 8000

# Healthcheck: usa tu /healthz
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

# Comando (Gunicorn)
CMD ["gunicorn", "-w", "2", "-k", "gthread", "-b", "0.0.0.0:8000", "app:app"]
