FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install core dependencies (fast)
COPY requirements-core.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements-core.txt

# Copy and install ML dependencies (heavy, with retry logic)
COPY requirements-ml.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements-ml.txt || \
    pip install --no-cache-dir --default-timeout=2000 -r requirements-ml.txt

# Copy application code
COPY app ./app

# Download spaCy model with retries to handle transient 502 network errors
RUN for i in 1 2 3 4 5; do \
        pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz && break || \
        (echo "Retry $i failed, sleeping 15s..." && sleep 15); \
    done

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application (app/main.py, not ./main.py)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
