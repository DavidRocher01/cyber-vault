FROM python:3.12-slim

# Apply OS security patches
RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

COPY . .

EXPOSE 8000
