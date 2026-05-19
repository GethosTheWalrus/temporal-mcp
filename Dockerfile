# Dockerfile for Temporal MCP Server (stdio-based)

FROM python:3.14-alpine AS builder

WORKDIR /app

# temporalio may compile from source on musl/Alpine
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    openssl-dev \
    protobuf \
    protobuf-dev \
    rust \
    cargo

COPY requirements.txt .

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade packaging tools before dependency install
RUN pip install --no-cache-dir --upgrade "pip>=26.0" "wheel>=0.46.2" "setuptools>=75.0"
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.14-alpine AS runtime

WORKDIR /app

RUN apk add --no-cache \
    libgcc \
    libstdc++

ENV PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

# Copy the application code
COPY server.py .
COPY pyproject.toml .
COPY temporal_mcp/ ./temporal_mcp/

# Default cert directory for mTLS (mount certs here at runtime)
RUN mkdir -p /certs

# Run via stdio - this is the MCP standard
CMD ["python", "-u", "server.py"]
