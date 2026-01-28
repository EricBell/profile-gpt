# ProfileGPT

An AI-powered web application that lets recruiters ask questions about Eric Bell. Uses OpenAI's API to generate responses reflecting Eric's personality, experience, and professional background.

## Why This Exists

Recruiters often have preliminary questions before scheduling calls. This app provides an interactive way to learn about a candidate's qualifications, experience, and working style without requiring direct contact for initial screening.

## Tech Stack

- **Backend**: Python Flask + Gunicorn
- **AI**: OpenAI Chat Completions API (gpt-4o-mini)
- **Package Manager**: uv
- **Containerization**: Docker
- **Deployment**: Dokploy-ready

## Quick Start

### Local Development

```bash
# Install dependencies
uv venv
uv pip install -e .

# Create .env from template
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and FLASK_SECRET_KEY

# Run
uv run python app.py --mode=local
```

Open http://localhost:5000

### Docker

```bash
# Build
docker build -t profile-gpt .

# Run
docker run -p 5000:5000 --env-file .env \
  -v $(pwd)/persona.txt:/data/persona.txt \
  -v $(pwd)/logs:/data/logs \
  profile-gpt
```

### Docker Compose

```bash
docker-compose up -d
```

## Features

**Two Interaction Modes:**
1. **Chat** - Ask questions about experience, skills, working style
2. **Job Fit** - Paste a job description to get a match analysis with scores

**Other Features:**
- Session-based query limiting (default: 20 queries)
- Conversation context maintained within session
- Hot-swappable persona file (no redeploy needed)
- Query logging for analytics
- Health check endpoint for monitoring

## Project Structure

```
profile-gpt/
├── app.py                 # Flask application
├── job_vetting.py         # Job fit analysis logic
├── version.py             # Version string
├── persona.txt            # AI system instructions (mounted at runtime)
├── templates/
│   └── index.html         # Web interface
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml         # Dependencies
├── .env.example           # Environment template
├── Intentions.md          # AI behavior guidelines
└── PRD.md                 # Full product requirements
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `FLASK_SECRET_KEY` | Yes | - | Secret for session signing |
| `ADMIN_RESET_KEY` | No | - | Secret key for `/reset` endpoint |
| `PERSONA_FILE_PATH` | No | `./persona.txt` | Path to persona instructions |
| `QUERY_LOG_PATH` | No | `./logs` | Directory for query logs |
| `MAX_QUERIES_PER_SESSION` | No | `20` | Query limit per session |
| `MAX_QUERY_LENGTH` | No | `500` | Max characters per query |
| `MAX_JOB_DESCRIPTION_LENGTH` | No | `5000` | Max chars for job descriptions |
| `PORT` | No | `5000` | Server port |

### Generating Secret Keys

**CRITICAL SECURITY REQUIREMENT:** Never use weak or default secret keys in production. The application enforces strong secrets in production mode and will refuse to start with weak values.

Generate secure keys:

```bash
# Flask session secret (required, 32+ characters)
python -c "import secrets; print(secrets.token_hex(32))"

# Admin reset key (optional, 16+ characters recommended)
python -c "import secrets; print(secrets.token_hex(16))"
```

**Local Development Mode:**
- Run with `--mode=local` flag
- Auto-generates secure keys if not set
- Warns about weak keys but allows them for convenience

**Production/Container Mode:**
- Requires `FLASK_SECRET_KEY` to be set with 32+ characters
- Refuses known weak values (e.g., 'dev', 'test', '4737d354')
- Will not start if secret validation fails

### Persona File

The `persona.txt` file contains system instructions that define how the AI responds. It's mounted at runtime (not baked into the container) so you can update it without redeploying.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/health` | GET | Health check (returns `{"status": "healthy"}`) |
| `/chat` | POST | Send chat message |
| `/vet` | POST | Analyze job description |
| `/status` | GET | Session status (query count, etc.) |
| `/reset?key=XXX` | GET | Admin: reset session (requires `ADMIN_RESET_KEY`) |

## Deployment

### Dokploy (Recommended)

**Option 1: Docker Compose**
1. Create a "Compose" application in Dokploy
2. Point to this repository
3. Set environment variables in Dokploy UI
4. Configure volumes for `persona.txt` and `logs/`

**Option 2: Dockerfile**
1. Create a "Docker" application in Dokploy
2. Point to this repository
3. Set environment variables
4. Add volume mounts:
   - `./persona.txt:/data/persona.txt:ro`
   - `./logs:/data/logs`

The app exposes `/health` for container health monitoring.

## Security

- **Prompt injection protection**: Input sanitization strips common injection patterns
- **Session-based rate limiting**: Prevents API cost abuse
- **Signed sessions**: Flask secret key prevents cookie tampering
- **Credentials**: API keys via environment variables, never committed

## Development

### Running Tests

```bash
uv run pytest
```

### Version Management

Version follows `MAJOR.MINOR.PATCH` format. Update both `version.py` and `pyproject.toml` when changing versions.

## License

Private project.
