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
```

## Guiding Document

**See [Intentions.md](Intentions.md)** - This file defines the core principles that guide all development decisions for this project. The AI persona, response style, and interaction patterns described there should inform every feature and implementation choice.

## Version Management

Version format: MAJOR.MINOR.PATCH (starting at 0.1.0)

**Incrementing rules:**
- MINOR: Increment when completing a new feature set
- PATCH: Increment when fixing a bug or set of bugs in one turn
- MAJOR: Only increment when instructed by the user (resets MINOR and PATCH to 0)

Update both `version.py` and `pyproject.toml` when changing versions.
