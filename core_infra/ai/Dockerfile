FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies including AI/ML libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional AI/ML packages
RUN pip install --no-cache-dir \
    torch \
    transformers \
    sentence-transformers \
    openai \
    anthropic \
    langchain \
    langsmith

# Copy application code
COPY core_infra/ ./core_infra/
COPY . .

# Create directories for models and cache
RUN mkdir -p /app/models_cache /app/logs && \
    adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8001

# Run the AI insights service
CMD ["python", "-m", "core_infra.ai.embeddings"] 