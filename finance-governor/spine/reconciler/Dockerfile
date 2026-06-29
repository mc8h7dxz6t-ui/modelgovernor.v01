FROM python:3.12-slim
WORKDIR /app/finance-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY finance-governor/spine/sidecar/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY governor-spine-core /app/governor-spine-core
COPY finance-governor /app/finance-governor
ENV PYTHONPATH=/app/governor-spine-core:/app/finance-governor/spine/sidecar:/app/finance-governor/spine/reconciler:/app/finance-governor
WORKDIR /app/finance-governor/spine/reconciler
CMD ["python", "-m", "app.main"]
