FROM python:3.12-slim
WORKDIR /app/finance-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY finance-governor/spine/sidecar/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY finance-governor /app/finance-governor
ENV PYTHONPATH=/app/finance-governor/spine/sidecar:/app/finance-governor
WORKDIR /app/finance-governor/spine/sidecar
RUN useradd --create-home --uid 1000 fgsidecar
USER fgsidecar
EXPOSE 8091
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8091"]
