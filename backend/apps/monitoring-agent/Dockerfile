FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY src/ ./src/

ENV PYTHONUNBUFFERED=1
ENV REDIS_HOST=edge-cache

# Run the exporter script
CMD ["python", "src/exporter.py"]
