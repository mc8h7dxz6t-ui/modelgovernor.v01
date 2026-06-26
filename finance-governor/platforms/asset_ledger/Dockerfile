FROM python:3.12-slim
WORKDIR /app/finance-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/finance-governor
COPY finance-governor/platforms/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY finance-governor/platforms/common ./platforms/common
COPY finance-governor/platforms/asset_ledger ./platforms/asset_ledger
EXPOSE 8096
CMD ["uvicorn", "platforms.asset_ledger.main:app", "--host", "0.0.0.0", "--port", "8096"]
