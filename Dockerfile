# ==============================================================================
# CricImpact Backend — Google Cloud Run Dockerfile
# ==============================================================================
# Multi-stage / lightweight production container for FastAPI backend.
# Complies with Cloud Run container runtime contract:
# - Listens on 0.0.0.0 and dynamically injected $PORT (default 8080)
# - Sends logs directly to stdout/stderr
# - Handles SIGTERM gracefully via PID 1 exec
# ==============================================================================

FROM python:3.11-slim

# Set environment variables for production execution
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Set working directory inside container
WORKDIR /app

# Install dependencies first to maximize Docker layer cache efficiency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code and scoring engine
COPY app/ app/
COPY src/ src/

# Copy processed datasets and model artifacts required at runtime
COPY data/processed/ data/processed/
COPY models/ models/

# Create a non-privileged user and transfer ownership for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose standard Cloud Run port
EXPOSE 8080

# Launch FastAPI using Uvicorn on 0.0.0.0:${PORT:-8080}
# 'exec' replaces the shell with Uvicorn as PID 1 to ensure immediate SIGTERM handling
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
