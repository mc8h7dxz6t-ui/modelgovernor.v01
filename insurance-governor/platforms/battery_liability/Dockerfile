FROM python:3.12-slim
WORKDIR /app/insurance-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/insurance-governor
COPY insurance-governor/platforms/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY insurance-governor/platforms/common ./platforms/common
COPY insurance-governor/platforms/battery_liability ./platforms/battery_liability
EXPOSE 8108
CMD ["uvicorn", "platforms.battery_liability.main:app", "--host", "0.0.0.0", "--port", "8108"]
