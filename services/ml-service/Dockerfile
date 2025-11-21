# ============= ML SERVICE DOCKERFILE =============
# Multi-stage build for ml-service with optional GPU support

FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (CPU version)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY models/ ./models/

# Create non-root user
RUN useradd -m -u 1000 mlservice && \
    chown -R mlservice:mlservice /app
USER mlservice

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]


# ============= GPU VARIANT (OPTIONAL) =============
# To build with GPU support:
# docker build --target gpu -t ml-service:gpu .

FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 as gpu

WORKDIR /app

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python
RUN ln -s /usr/bin/python3.11 /usr/bin/python

# Copy requirements
COPY requirements.txt .

# Install Python dependencies with GPU support
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir tensorflow[and-cuda]==2.15.0

# Copy application code
COPY app/ ./app/
COPY models/ ./models/

# Create non-root user
RUN useradd -m -u 1000 mlservice && \
    chown -R mlservice:mlservice /app
USER mlservice

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
