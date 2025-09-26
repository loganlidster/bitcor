FROM python:3.11-slim

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# IMPORTANT: listen on 0.0.0.0:8080 so ALB can reach the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
