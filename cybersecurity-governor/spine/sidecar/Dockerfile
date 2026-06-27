FROM python:3.12-slim
WORKDIR /app/cybersecurity-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY cybersecurity-governor/spine/sidecar/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cybersecurity-governor /app/cybersecurity-governor
ENV PYTHONPATH=/app/cybersecurity-governor/spine/sidecar:/app/cybersecurity-governor
WORKDIR /app/cybersecurity-governor/spine/sidecar
RUN useradd --create-home --uid 1000 cgsidecar
USER cgsidecar
EXPOSE 8121
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8121"]
