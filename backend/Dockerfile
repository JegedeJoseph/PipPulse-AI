FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
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
COPY main.py .

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
