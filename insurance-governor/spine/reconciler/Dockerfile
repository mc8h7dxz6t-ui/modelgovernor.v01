FROM python:3.12-slim
WORKDIR /app/insurance-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY insurance-governor/spine/reconciler/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY governor-spine-core /app/governor-spine-core
COPY insurance-governor /app/insurance-governor
ENV PYTHONPATH=/app/governor-spine-core:/app/insurance-governor/spine/sidecar:/app/insurance-governor
WORKDIR /app/insurance-governor/spine/reconciler
CMD ["python", "-m", "app.main"]
