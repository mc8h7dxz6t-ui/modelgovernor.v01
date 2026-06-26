FROM python:3.12-slim
WORKDIR /app/cyber-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY cyber-governor/platforms/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cyber-governor /app/cyber-governor
ENV PYTHONPATH=/app/cyber-governor
WORKDIR /app/cyber-governor/platforms/content_guard
EXPOSE 8108
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8108"]
