# Product Requirements Document: ProfileGPT

## 1. Overview

ProfileGPT is an AI-powered web application that allows recruiters to ask questions about Eric Bell. The application uses OpenAI's API to generate responses that reflect Eric's personality, experience, and professional background.

### 1.1 Purpose
Provide recruiters with an interactive way to learn about Eric Bell's qualifications, experience, and working style without requiring direct contact for initial screening questions.

### 1.2 Project Goal
Deploy a production-ready web application to a Dokploy-managed VPS. All development is done locally, with the application containerized and ready for deployment to the VPS.

### 1.3 Access Model
This is a **public website** with no authentication. Anyone can access and use the application. To control costs, usage is limited per session via a configurable query limit.

### 1.4 Target Users
- Recruiters evaluating Eric as a candidate
- Hiring managers seeking preliminary information
- HR professionals conducting initial assessments

---

## 2. Functional Requirements

### 2.1 Core Features

#### 2.1.1 Chat Interface
- **ChatGPT-style UI**: Large, prominent text input box for natural language questions
- Responses displayed in a conversational format with clear visual distinction between user questions and AI responses
- Clean, minimal, professional interface
- Message history visible within the current session
- Clear indication when query limit is reached

#### 2.1.2 AI Response Generation
- Responses must reflect Eric Bell's persona as defined in `Intentions.md`
- Concise answers are preferred over verbose responses
- The AI may ask clarifying questions when the user's question is ambiguous
- When information is unknown, the AI should honestly state so rather than fabricate

#### 2.1.3 Conversation Context
- The application should maintain conversation context within a session
- Users should be able to ask follow-up questions that reference previous exchanges

#### 2.1.4 Health Check Endpoint
- Provide a `/health` endpoint for container monitoring
- Returns HTTP 200 when the application is healthy
- Used by Dokploy for container health monitoring

#### 2.1.5 Session-Based Usage Limiting
- Each browser session has a configurable maximum number of queries
- Query count tracked server-side using Flask sessions
- When limit is reached:
  - Text input is disabled
  - Clear message displayed explaining the limit has been reached
  - User can start a new session (e.g., new browser/incognito) if needed
- Query limit is configurable via environment variable (`MAX_QUERIES_PER_SESSION`)
- Default limit: 20 queries per session

---

## 3. Technical Architecture

### 3.1 Application Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Python Flask |
| WSGI Server | Gunicorn |
| AI Provider | OpenAI Responses API |
| Containerization | Docker |
| Base Image | Python slim variant |
| Deployment Platform | Dokploy on VPS |

### 3.2 Application Structure

```
profile-gpt/
├── app.py                 # Flask application entry point
├── persona.txt            # System instructions (mounted at runtime, not in container)
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container definition
├── docker-compose.yml     # Container orchestration (optional)
├── .env                   # API credentials (gitignored)
├── .env.example           # Template for environment variables
├── Intentions.md          # Developer guidelines for AI behavior
├── PRD.md                 # This document
└── templates/             # HTML templates (if using server-side rendering)
    └── index.html
```

### 3.3 Execution Modes

The application must support two execution modes controlled via command-line arguments:

#### Local Development Mode
- Runs Flask's built-in development server
- Hot-reloading enabled for rapid development
- Debug mode available
- Example: `python app.py --mode=local`

#### Container/Production Mode
- Runs via Gunicorn WSGI server
- Optimized for production workloads
- Example: `python app.py --mode=container` or via Docker

---

## 4. API Integration

### 4.1 OpenAI Responses API

#### 4.1.1 Configuration
- API key stored in `.env` file
- Never commit credentials to version control

#### 4.1.2 System Instructions
- Stored in `persona.txt` (or similar file)
- **Hot-swappable**: File is mounted from host filesystem, not baked into container
- Can be updated on the server without redeploying the container
- Application reads the file on each request (or with reasonable caching)
- Defines Eric Bell's persona, background, and response guidelines
- Should incorporate principles from `Intentions.md`

#### 4.1.3 Request Handling
- User messages sent to OpenAI API with system instructions
- Conversation history maintained for context
- Appropriate error handling for API failures

---

## 5. Configuration Management

### 5.1 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | API key for OpenAI | Yes |
| `FLASK_SECRET_KEY` | Secret key for Flask sessions | Yes |
| `PERSONA_FILE_PATH` | Path to persona.txt (default: `/data/persona.txt` in container, `./persona.txt` locally) | No |
| `MAX_QUERIES_PER_SESSION` | Maximum queries per session (default: 20) | No |
| `MAX_QUERY_LENGTH` | Maximum characters per query (default: 500) | No |
| `FLASK_ENV` | Environment (development/production) | No |
| `PORT` | Server port (default: 5000, set by Dokploy in production) | No |

### 5.2 Configuration Files

- `.env` - Contains sensitive credentials, gitignored
- `.env.example` - Template showing required variables without values
- `persona.txt` - System instructions for AI persona

---

## 6. Deployment

### 6.1 Development Workflow

All development is done locally. The application must work in both local and containerized modes before deployment.

#### 6.1.1 Local Development (without Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py --mode=local
```

#### 6.1.2 Local Container Testing
```bash
# Build container
docker build -t profile-gpt .

# Run container locally with mounted persona file
docker run -p 5000:5000 --env-file .env \
  -v $(pwd)/persona.txt:/data/persona.txt \
  profile-gpt
```

### 6.2 Docker Configuration

#### 6.2.1 Dockerfile Requirements
- Use official Python slim image as base
- Install only necessary dependencies
- Copy application code (but NOT the persona file)
- Expose appropriate port
- Set Gunicorn as the entry point for production
- Container must be stateless and ready for Dokploy deployment

#### 6.2.2 Volume Mount for System Instructions
The `persona.txt` file must be mounted from the host filesystem:
- Allows updating AI persona without container redeployment
- Upload new file to server, changes take effect immediately
- Application should read from a configurable path (e.g., `/data/persona.txt`)

### 6.3 Production Deployment (Dokploy VPS)

#### 6.3.1 Deployment Target
- Platform: Dokploy
- Infrastructure: VPS
- The Docker container is deployed via Dokploy's container management

#### 6.3.2 Dokploy Requirements
- Dockerfile must be present in repository root
- Environment variables configured in Dokploy dashboard
- Volume mount configured for `persona.txt` (host path → `/data/persona.txt`)
- Health check endpoint recommended for container monitoring
- Application should listen on the port specified by `PORT` environment variable

#### 6.3.3 Deployment Checklist
- [ ] Application tested locally without Docker
- [ ] Application tested locally with Docker
- [ ] Dockerfile builds successfully
- [ ] Environment variables documented in `.env.example`
- [ ] Application responds to health checks
- [ ] Ready for Dokploy deployment

---

## 7. Security Considerations

### 7.1 Credential Management
- API keys must never be committed to version control
- Use `.env` files for local development
- Use environment variables or secrets management for production
- Flask secret key must be set for secure session management

### 7.2 Prompt Injection Protection
User input must be sanitized and validated to prevent prompt injection attacks:
- **Input length limits**: Maximum character limit on user queries
- **System prompt isolation**: Keep system instructions separate and immutable from user input
- **Input sanitization**: Strip or escape potentially malicious patterns
- **Role enforcement**: Never allow user input to override the AI's persona or system instructions
- **Output monitoring**: The AI should refuse requests that attempt to:
  - Reveal system prompts
  - Assume a different persona
  - Execute commands or access external systems
  - Bypass conversation context

### 7.3 Session-Based Rate Limiting
- Query limits enforced server-side via Flask sessions
- Prevents excessive API usage and associated costs
- Session data stored server-side (not in client-manipulable cookies)

### 7.4 API Security
- HTTPS required in production (handled by Dokploy/reverse proxy)
- CORS configured appropriately for the deployment domain

---

## 8. Testing Strategy

### 8.1 Local Testing (without Docker)
```bash
python app.py --mode=local
```
- Verify chat interface loads with ChatGPT-style input
- Test question/answer flow
- Confirm persona is reflected in responses
- Test session query limit (exhaust limit, verify lockout message)
- Test prompt injection attempts (try to override persona, reveal system prompt)

### 8.2 Container Testing
```bash
docker build -t profile-gpt .
docker run -p 5000:5000 --env-file .env profile-gpt
```
- Verify container builds successfully
- Confirm application responds correctly
- Test same functionality as local mode
- Verify session persistence works in container

### 8.3 Security Testing
- Attempt to bypass query limits via session manipulation
- Test various prompt injection patterns
- Verify input length limits are enforced

---

## 9. Success Criteria

- [ ] Application runs locally with Flask dev server
- [ ] Application runs in Docker container with Gunicorn
- [ ] ChatGPT-style interface with large text input box
- [ ] Responses reflect Eric Bell's persona per `Intentions.md`
- [ ] Conversation context is maintained within a session
- [ ] Session-based query limiting works correctly
- [ ] Query limit is configurable via environment variable
- [ ] Persona file is hot-swappable without redeployment
- [ ] Prompt injection attempts are blocked or handled safely
- [ ] API credentials are properly secured
- [ ] Application handles API errors gracefully
- [ ] Application deployed and running on Dokploy VPS

---

## 10. Future Considerations

These items are out of scope for initial implementation but may be considered later:

- Conversation history persistence
- Analytics on common questions
- IP-based rate limiting (in addition to session-based)
- Custom domain configuration on Dokploy
- Enhanced prompt injection detection
