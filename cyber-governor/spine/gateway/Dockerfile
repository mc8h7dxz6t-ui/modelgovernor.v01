FROM python:3.12-slim
WORKDIR /app/cyber-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY cyber-governor/spine/gateway/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cyber-governor/spine/gateway/app ./spine/gateway/app
WORKDIR /app/cyber-governor/spine/gateway
EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
