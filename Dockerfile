FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    tor \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Start Tor in background
CMD tor & python main.py
