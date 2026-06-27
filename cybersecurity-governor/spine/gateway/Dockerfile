FROM python:3.12-slim
WORKDIR /app/cybersecurity-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY cybersecurity-governor/spine/gateway/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cybersecurity-governor/spine/gateway ./spine/gateway
ENV PYTHONPATH=/app/cybersecurity-governor/spine/gateway
WORKDIR /app/cybersecurity-governor/spine/gateway
EXPOSE 8120
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8120"]
