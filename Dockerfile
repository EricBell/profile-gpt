# Copyright Polymorph Corporation (2026)

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

# Copy application code (NOT persona.txt or config.json - those are mounted at runtime)
COPY app.py .
COPY version.py .
COPY messages.py .
COPY job_vetting.py .
COPY query_logger.py .
COPY config_validator.py .
COPY intent_classifier.py .
COPY dataset_manager.py .
COPY email_detector.py .
COPY extension_manager.py .
COPY email_notifier.py .
COPY usage_tracker.py .
COPY templates/ templates/
COPY static/ static/
COPY analyze_logs.py .
COPY config.example.json /data/config.json

# Create data directory for volume mounts
# - /data/persona.txt: AI persona instructions (mount from host)
# - /data/config.json: Hot-tunable settings (mount from host for runtime tuning)
# - /data/logs: Query logs directory (mount from host for persistence)
RUN mkdir -p /data/logs

# Declare volumes for external mount points
# VOLUME ["/data"]

# Set default environment variables
ENV PORT=5000
ENV PERSONA_FILE_PATH=/data/persona.txt
ENV CONFIG_FILE_PATH=/data/config.json
ENV QUERY_LOG_PATH=/data/logs

# CRITICAL: Set these environment variables when running the container!
# Generate secure keys with: python -c "import secrets; print(secrets.token_hex(32))"
ENV OPENAI_API_KEY=
ENV OPENAI_ADMIN_API_KEY=
ENV FLASK_SECRET_KEY=
ENV ADMIN_RESET_KEY=
ENV MAX_QUERIES_PER_SESSION=20
ENV MAX_QUERY_LENGTH=500
ENV FLASK_ENV=development

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Run with Gunicorn
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app:app"]
# Added --access-logfile - to print request logs to stdout
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--access-logfile", "-", "app:app"]
