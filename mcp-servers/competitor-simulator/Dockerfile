FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl gcc postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3002

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3002/health || exit 1

CMD ["python", "server.py"]
