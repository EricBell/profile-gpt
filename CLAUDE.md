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

## Version Management

Version format: MAJOR.MINOR.PATCH (starting at 0.1.0)

**Incrementing rules:**
- MINOR: Increment when completing a new feature set
- PATCH: Increment when fixing a bug or set of bugs in one turn
- MAJOR: Only increment when instructed by the user (resets MINOR and PATCH to 0)

Update both `version.py` and `pyproject.toml` when changing versions.

## Copyright Notice Requirements

**All new files should include a copyright notice when applicable:**

1. **Format**: `Copyright Polymorph Corporation (YYYY)` where YYYY is the current year (e.g., 2026)

2. **File Types & Placement**:
   - **Code files** (.py, .js, .css, etc.): Add as comment at top of file
   - **Config files** (.yml, .toml, .json, etc.): Add as comment if format supports it
   - **Documentation** (.md): Optional - may be omitted for pure documentation files

3. **Comment Style**: Always use appropriate comment syntax for the file type:
   ```python
   # Copyright Polymorph Corporation (2026)
   ```
   ```yaml
   # Copyright Polymorph Corporation (2026)
   ```

4. **Updating Existing Files**: If a copyright notice already exists, update the year to current year if not already included

## Deployment Checklist

**When adding new Python modules or features, ALWAYS update these files:**

1. **`Dockerfile`** - Add new `.py` modules to the COPY commands (around line 25-33)
2. **`version.py`** and **`pyproject.toml`** - Increment version per rules above
3. **`app.py`** - Add imports and route handlers as needed
4. **`templates/`** - Add any new HTML templates
5. **`static/`** - Add any new CSS/JS files

**Docker deployment uses explicit file listing** - if you create a new Python module and don't add it to the Dockerfile, it won't be included in the Docker image and the app will fail to start.

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

## Intention Monitoring System

ProfileGPT uses intention-based monitoring to ensure quality interactions and prevent runaway token usage:

**Session Limits:**
- Total session limit: 50 questions (prevents runaway token usage)
- OUT_OF_SCOPE query limits: Warning at 5, cutoff at 10 (prevents abuse)
- IN_SCOPE queries: Limited only by total session limit

**Thresholds:**
- Total session limit: 50 questions
- OUT_OF_SCOPE warning: 5 questions
- OUT_OF_SCOPE cutoff: 10 questions

**User Experience:**
- Users who stay on-topic can ask up to 50 professional questions
- Off-topic questions receive polite refusal messages
- Warning message at 5 off-topic questions: "You're straying away from Eric's professional life too much. I'll cut you off if you continue."
- At 10 off-topic questions OR 50 total questions: Session limited, user can request reset via email

**Reset Request System:**

If a legitimate user hits any limit, they can submit their email to request a manual session reset. Admin reviews and approves, which clears all counters and gives them a fresh session.

1. **User Flow:**
   - User hits limit (total session or out-of-scope cutoff)
   - System prompts: "To request a session reset, send a message with your email address"
   - User types email in chat
   - System detects email, creates reset request, sends notification to admin
   - User receives confirmation message

2. **Admin Workflow:**
   - Eric receives email notification when reset request is created
   - Admin visits `/extension-requests?key=YOUR_KEY` to review pending requests
   - Admin approves/denies reset requests
   - Approved sessions get all counters cleared (in_scope_count, out_of_scope_count, total_turns reset to 0)

3. **Required Environment Variables:**
   ```bash
   # Session limits
   MAX_QUERIES_PER_SESSION=50
   OUT_OF_SCOPE_WARNING_THRESHOLD=5
   OUT_OF_SCOPE_CUTOFF_THRESHOLD=10

   # Email notifications
   ADMIN_EMAIL=eric@example.com
   APP_URL=https://your-app-domain.com
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

4. **Key Files:**
   - `intent_classifier.py` - LLM-based intent classification and warning messages
   - `email_detector.py` - Email extraction/validation
   - `extension_manager.py` - Reset request management (CRUD)
   - `email_notifier.py` - SMTP email notifications
   - `templates/extension_requests.html` - Admin UI
   - `logs/extension_requests.ndjson` - Reset request log
   - `logs/approved_resets.json` - Session reset approval tracking

## Guiding Document

**See [Intentions.md](Intentions.md)** - This file defines the core principles that guide all development decisions for this project. The AI persona, response style, and interaction patterns described there should inform every feature and implementation choice.
