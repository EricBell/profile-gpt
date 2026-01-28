# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProfileGPT is an AI-powered "Ask Eric" web app for recruiters. It uses OpenAI's Responses API to simulate Eric Bell's personality and experience when answering questions.

## Tech Stack

- Python Flask web framework
- Gunicorn WSGI server
- OpenAI Responses API
- uv package manager
- Docker (slim Python image)

## Configuration

- API credentials: `.env` file (gitignored)
- AI persona/system instructions: stored in a local file accessible to the Flask app

## Running the App

```bash
# Local development
uv venv
uv pip install -e .
uv run python app.py --mode=local

# Docker
docker build -t profile-gpt .
docker run -p 5000:5000 --env-file .env \
  -v $(pwd)/persona.txt:/data/persona.txt \
  -v $(pwd)/logs:/data/logs \
  profile-gpt

# Docker Compose
docker-compose up -d
```

## Dokploy Deployment

This app is ready for deployment on Dokploy (self-hosted PaaS).

**Option 1: Docker Compose (Recommended)**
1. In Dokploy, create a new "Compose" application
2. Point to this repository
3. Set environment variables in Dokploy UI:
   - `OPENAI_API_KEY` (required)
   - `FLASK_SECRET_KEY` (required - MUST be 32+ characters, generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `ADMIN_RESET_KEY` (optional - if set, should be 16+ characters for security)
4. Configure volumes for persistent data (`persona.txt`, `logs/`)

**CRITICAL:** The application will refuse to start if `FLASK_SECRET_KEY` is not set or uses a weak/known value. Never use example values from documentation in production.

**Option 2: Dockerfile**
1. Create a new "Docker" application
2. Point to this repository (uses Dockerfile)
3. Set environment variables in Dokploy UI (same requirements as above)
4. Add volume mounts:
   - `./persona.txt:/data/persona.txt:ro`
   - `./logs:/data/logs`

**Health Check:** The app exposes `/health` endpoint for container monitoring.

## Guiding Document

**See [Intentions.md](Intentions.md)** - This file defines the core principles that guide all development decisions for this project. The AI persona, response style, and interaction patterns described there should inform every feature and implementation choice.

## Version Management

Version format: MAJOR.MINOR.PATCH (starting at 0.1.0)

**Incrementing rules:**
- MINOR: Increment when completing a new feature set
- PATCH: Increment when fixing a bug or set of bugs in one turn
- MAJOR: Only increment when instructed by the user (resets MINOR and PATCH to 0)

Update both `version.py` and `pyproject.toml` when changing versions.
