# Dockerfile for Temporal MCP Server (stdio-based)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY server.py .
COPY pyproject.toml .

# Install dependencies directly (no package install needed)
# temporal_mcp package is only needed by worker

# Set environment variable for Temporal host
# Use host.docker.internal to reach services on the host machine
ENV TEMPORAL_HOST=host.docker.internal:7233

# Run via stdio - this is the MCP standard
CMD ["python", "-u", "server.py"]
