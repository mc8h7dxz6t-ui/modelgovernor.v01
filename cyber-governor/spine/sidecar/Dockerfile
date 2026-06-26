FROM python:3.12-slim
WORKDIR /app/cyber-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY cyber-governor/spine/sidecar/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cyber-governor /app/cyber-governor
ENV PYTHONPATH=/app/cyber-governor/spine/sidecar:/app/cyber-governor
WORKDIR /app/cyber-governor/spine/sidecar
RUN useradd --create-home --uid 1000 fgsidecar
USER fgsidecar
EXPOSE 8101
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8101"]
