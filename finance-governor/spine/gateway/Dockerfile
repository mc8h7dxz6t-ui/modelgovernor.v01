FROM python:3.12-slim
WORKDIR /app/finance-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY finance-governor/spine/gateway/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY finance-governor/spine/gateway/app ./spine/gateway/app
WORKDIR /app/finance-governor/spine/gateway
EXPOSE 8090
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
