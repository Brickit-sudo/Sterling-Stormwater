FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure runtime directories exist
RUN mkdir -p projects output /appdata

ENV DB_DIR=/appdata

EXPOSE 8501

ENV PYTHONUNBUFFERED=1

COPY start.py .
CMD ["python", "start.py"]
