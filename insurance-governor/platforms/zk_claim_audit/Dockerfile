FROM python:3.12-slim
WORKDIR /app/insurance-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/insurance-governor
COPY insurance-governor/platforms/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY insurance-governor/platforms/common ./platforms/common
COPY insurance-governor/platforms/zk_claim_audit ./platforms/zk_claim_audit
EXPOSE 8106
CMD ["uvicorn", "platforms.zk_claim_audit.main:app", "--host", "0.0.0.0", "--port", "8106"]
