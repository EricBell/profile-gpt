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
- Hot-tunable settings: `config.json` (re-read on each request, no restart needed)

### Hot-Tunable Settings

You can configure `conversation_history_limit` (how many previous messages to include in OpenAI API context) in two ways:

#### Option 1: Environment Variable (Set Once)
Add to your `.env` file or Dokploy environment variables:
```bash
CONVERSATION_HISTORY_LIMIT=10
```
Requires container restart to take effect.

#### Option 2: Hot-Reload via config.json (Runtime Tuning)
For runtime tuning without restart, use `config.json`:

```json
{
  "conversation_history_limit": 10
}
```

**Setup for hot-reload (Dokploy):**
1. In Dokploy, go to your app's "Files" tab
2. Create a new file: `config.json`
3. Add the JSON content above
4. Edit `docker-compose.yml` and uncomment the config.json volume mount line
5. Redeploy the container

**After setup:**
- Edit `config.json` in Dokploy UI
- Changes take effect on next chat request (no restart needed)

**Available settings:**
- `conversation_history_limit`: Number of previous messages to include in OpenAI API context (default: 20)
  - Lower values = less token usage but less context
  - Higher values = more context but higher token costs
  - Set to 0 to keep all history (not recommended for cost control)
  - Recommended range: 3-20 depending on your use case

**Fallback:** The Docker image includes a default config.json (limit: 20). If you don't mount a custom config.json, it uses this default.

### Token Cost Optimization

To reduce OpenAI API token usage and costs:

1. **Lower conversation history limit:**
   - Edit `config.json` and set `conversation_history_limit` to a smaller value (e.g., 3, 5, or 10)
   - Lower values mean less conversation context is sent with each API call
   - Changes take effect immediately without restart

2. **Monitor token usage:**
   - Check your OpenAI API dashboard for usage metrics
   - Test with different `conversation_history_limit` values to find the sweet spot
   - Balance between cost (lower = cheaper) and quality (higher = better context)

3. **Example configurations:**
   - **Minimal context (lowest cost):** `{"conversation_history_limit": 3}`
   - **Moderate context:** `{"conversation_history_limit": 10}`
   - **Full context (default):** `{"conversation_history_limit": 20}`
   - **No limit (highest cost, not recommended):** `{"conversation_history_limit": 0}`

**Note:** Setting the limit too low may cause the AI to "forget" recent context and provide less coherent responses. Test to find the optimal balance for your use case.

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

## Usage Tracking System

ProfileGPT automatically tracks OpenAI API token usage and costs for all API calls:

**What's Tracked:**
- Per-request token usage (input tokens, output tokens, total tokens)
- Estimated costs based on current gpt-4o-mini pricing ($0.150/1M input, $0.600/1M output)
- Call type (classification, conversation, job_vetting)
- Query scope (IN_SCOPE, OUT_OF_SCOPE)
- Session ID and timestamp

**Usage Data Storage:**
- Logs stored in `logs/usage_tracking.ndjson` (one JSON object per line)
- Each record includes: session_id, timestamp, tokens, costs, model, call_type, scope

**Admin Dashboards:**
- **Local Usage Stats** (`/usage-stats?key=YOUR_ADMIN_KEY`):
  - View aggregate statistics (total calls, tokens, costs)
  - Breakdown by call type, scope, model, and date
  - Identify most expensive sessions
  - Filter by date range or session ID
  - Export data as JSON with `?format=json`

- **Usage API Comparison** (`/usage-api?key=YOUR_ADMIN_KEY`):
  - Compare local tracking with OpenAI's official Usage API data
  - Verify accuracy of local tracking
  - Identify discrepancies in token counts or costs
  - Reconcile billing data with internal logs
  - Supports date range filtering

**Key Metrics Available:**
- Total API calls and token usage
- Average tokens/cost per call
- Daily usage trends
- Cost breakdown by classification vs conversation
- Token savings from OUT_OF_SCOPE filtering
- Most expensive sessions (last 30 days)

**Use Cases:**
- Monitor API spending in real-time
- Validate conversation_history_limit optimization
- Identify expensive query patterns
- Budget forecasting and cost control
- Prove effectiveness of intent classification

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
