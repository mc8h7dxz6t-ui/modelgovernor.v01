FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/governor-spine-core:/app

COPY sidecar/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY governor-spine-core /app/governor-spine-core
COPY sidecar/app ./app

RUN useradd --create-home --uid 1000 sidecar
USER sidecar

EXPOSE 8081

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
