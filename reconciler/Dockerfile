FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY reconciler/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY reconciler/app ./app
COPY sidecar/app ./sidecar/app

RUN useradd --create-home --uid 1000 reconciler
USER reconciler

EXPOSE 8082

ENV RECONCILER_MODE=daemon

CMD ["python", "-m", "app.main"]
