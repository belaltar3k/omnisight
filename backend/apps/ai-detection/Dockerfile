FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/apps/ai-detection/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy AI components and pipeline (reuse research code)
COPY ai/components/ /app/ai/components/
COPY ai/pipeline/ /app/ai/pipeline/
COPY ai/surveillance_analytics/ /app/ai/surveillance_analytics/

# Copy the service source
COPY backend/apps/ai-detection/src/ /app/src/

ENV PYTHONPATH=/app:/app/ai
ENV PYTHONUNBUFFERED=1

EXPOSE 8010

CMD ["python", "-m", "src.main"]
