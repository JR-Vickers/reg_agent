# Use Python 3.11 slim image as base
# "slim" means it has fewer pre-installed packages, making it smaller
FROM python:3.11-slim

# Set working directory inside the container
# All commands will run from this directory
WORKDIR /app

# Install system dependencies
# These are needed for some Python packages to compile
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first
# Docker caches layers, so if dependencies don't change,
# it won't reinstall them even if code changes
COPY pyproject.toml ./
RUN mkdir -p src && touch src/__init__.py

# Install Python dependencies
# --no-cache-dir saves space by not caching downloads
RUN pip install --no-cache-dir --upgrade pip
# Install just the dependencies (not in editable mode)
RUN pip install --no-cache-dir .

# Copy the rest of the application code
COPY . .

# Expose port 8000 (FastAPI's default)
# This doesn't actually open the port, just documents it
EXPOSE 8000

# Command to run when container starts
# This will start your FastAPI application
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}