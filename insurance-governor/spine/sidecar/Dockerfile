FROM python:3.12-slim
WORKDIR /app/insurance-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY insurance-governor/spine/sidecar/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY insurance-governor /app/insurance-governor
ENV PYTHONPATH=/app/insurance-governor/spine/sidecar:/app/insurance-governor
WORKDIR /app/insurance-governor/spine/sidecar
RUN useradd --create-home --uid 1000 igsidecar
USER igsidecar
EXPOSE 8101
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8101"]
