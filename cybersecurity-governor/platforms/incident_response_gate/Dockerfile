FROM python:3.12-slim
WORKDIR /app/cybersecurity-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/cybersecurity-governor
COPY cybersecurity-governor/platforms/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cybersecurity-governor/platforms/common ./platforms/common
COPY cybersecurity-governor/platforms/incident_response_gate ./platforms/incident_response_gate
EXPOSE 8126
CMD ["uvicorn", "platforms.incident_response_gate.main:app", "--host", "0.0.0.0", "--port", "8126"]
