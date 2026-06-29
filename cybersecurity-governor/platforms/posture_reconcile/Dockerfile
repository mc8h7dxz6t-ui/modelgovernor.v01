FROM python:3.12-slim
WORKDIR /app/cybersecurity-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/cybersecurity-governor
COPY cybersecurity-governor/platforms/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cybersecurity-governor/platforms/common ./platforms/common
COPY cybersecurity-governor/platforms/posture_reconcile ./platforms/posture_reconcile
EXPOSE 8127
CMD ["uvicorn", "platforms.posture_reconcile.main:app", "--host", "0.0.0.0", "--port", "8127"]
