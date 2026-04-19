FROM python:3.11-slim

WORKDIR /app

# Dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Cache directory
RUN mkdir -p cache

# Default: run REST API on port 8080
EXPOSE 8080

ENV PYTHONUNBUFFERED=1

CMD ["python", "api.py", "--port", "8080", "--host", "0.0.0.0"]
