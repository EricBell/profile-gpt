FROM python:3.12-slim

WORKDIR /app

# install a tiny editor (vim-tiny) or nano
RUN apt-get update \
 && apt-get install -y --no-install-recommends vim-tiny \
 && rm -rf /var/lib/apt/lists/*

# or
# RUN apt-get update \
#  && apt-get install -y --no-install-recommends nano \
#  && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml .

# Install dependencies with uv
RUN uv pip install --system --no-cache .

# Copy application code (NOT persona.txt - that's mounted at runtime)
COPY app.py .
COPY version.py .
COPY job_vetting.py .
COPY templates/ templates/

# Create data directory for volume mounts
# - /data/persona.txt: AI persona instructions (mount from host)
# - /data/logs: Query logs directory (mount from host for persistence)
RUN mkdir -p /data/logs

# Declare volumes for external mount points
VOLUME ["/data"]

# Set default environment variables
ENV PORT=5000
ENV PERSONA_FILE_PATH=/data/persona.txt
ENV QUERY_LOG_PATH=/data/logs

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app:app"]
