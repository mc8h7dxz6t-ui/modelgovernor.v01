FROM python:3.12-slim
WORKDIR /app/cyber-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/cyber-governor
COPY cyber-governor/platforms/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cyber-governor /app/cyber-governor
EXPOSE 8103
CMD ["uvicorn", "platforms.identity_gate.main:app", "--host", "0.0.0.0", "--port", "8103"]
