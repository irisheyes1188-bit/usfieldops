FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FIELDOPS_HOST=0.0.0.0 \
    FIELDOPS_PORT=8765 \
    FIELDOPS_SERVE_FRONTEND=false \
    FIELDOPS_DATA_DIR=/data

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

RUN mkdir -p /data /secrets

EXPOSE 8765

CMD ["python", "backend/start_fastapi.py"]
