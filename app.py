import argparse
import os
import re
import sys
import uuid
from dataclasses import asdict
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from dotenv import load_dotenv

from version import __version__
from job_vetting import sanitize_job_description, evaluate_job_description
from query_logger import log_interaction
from config_validator import validate_flask_secret_key, validate_admin_reset_key

load_dotenv()

# Detect run mode early (before Flask app initialization)
is_local_mode = '--mode=local' in sys.argv

# Validate and set Flask secret key
flask_secret, flask_warning = validate_flask_secret_key(
    os.environ.get('FLASK_SECRET_KEY'),
    is_local_mode
)
if flask_warning:
    print(flask_warning, file=sys.stderr)

# Validate admin reset key if provided
admin_reset, admin_warning = validate_admin_reset_key(
    os.environ.get('ADMIN_RESET_KEY'),
    is_local_mode
)
if admin_warning:
    print(admin_warning, file=sys.stderr)

app = Flask(__name__)
app.secret_key = flask_secret

# Configuration
MAX_QUERIES_PER_SESSION = int(os.environ.get('MAX_QUERIES_PER_SESSION', 20))
MAX_QUERY_LENGTH = int(os.environ.get('MAX_QUERY_LENGTH', 500))
MAX_JOB_DESCRIPTION_LENGTH = int(os.environ.get('MAX_JOB_DESCRIPTION_LENGTH', 5000))
PERSONA_FILE_PATH = os.environ.get('PERSONA_FILE_PATH', './persona.txt')
QUERY_LOG_PATH = os.environ.get('QUERY_LOG_PATH', './logs')
ADMIN_RESET_KEY = admin_reset

# OpenAI client (lazy initialization)
_client = None


def get_openai_client():
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        _client = OpenAI(api_key=api_key)
    return _client


def load_persona():
    """Load persona instructions from file. Re-reads on each call for hot-swapping."""
    try:
        with open(PERSONA_FILE_PATH, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "You are a helpful assistant representing Eric Bell."


def sanitize_input(user_input):
    """Sanitize user input to prevent prompt injection."""
    if not user_input:
        return ""

    # Truncate to max length
    user_input = user_input[:MAX_QUERY_LENGTH]

    # Remove potential injection patterns
    # Strip attempts to override system instructions
    patterns_to_remove = [
        r'(?i)ignore\s+(all\s+)?(previous|above|prior)\s+instructions?',
        r'(?i)forget\s+(all\s+)?(previous|above|prior)\s+instructions?',
        r'(?i)disregard\s+(all\s+)?(previous|above|prior)\s+instructions?',
        r'(?i)you\s+are\s+now\s+',
        r'(?i)act\s+as\s+(if\s+you\s+are\s+)?',
        r'(?i)pretend\s+(to\s+be|you\s+are)\s+',
        r'(?i)system\s*:\s*',
        r'(?i)assistant\s*:\s*',
        r'(?i)user\s*:\s*',
    ]

    for pattern in patterns_to_remove:
        user_input = re.sub(pattern, '', user_input)

    return user_input.strip()


def get_query_count():
    """Get current query count from session."""
    return session.get('query_count', 0)


def increment_query_count():
    """Increment and return query count."""
    count = get_query_count() + 1
    session['query_count'] = count
    return count


def get_conversation_history():
    """Get conversation history from session."""
    return session.get('conversation', [])


def add_to_conversation(role, content):
    """Add a message to conversation history."""
    conversation = get_conversation_history()
    conversation.append({'role': role, 'content': content})
    # Keep last 20 messages to prevent context from growing too large
    session['conversation'] = conversation[-20:]


def get_session_id():
    """Get or create a unique session ID."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())[:8]
    return session['session_id']


@app.route('/')
def index():
    """Render the chat interface."""
    return render_template('index.html',
                         query_count=get_query_count(),
                         max_queries=MAX_QUERIES_PER_SESSION,
                         max_query_length=MAX_QUERY_LENGTH,
                         max_job_description_length=MAX_JOB_DESCRIPTION_LENGTH,
                         version=__version__)


@app.route('/health')
def health():
    """Health check endpoint for container monitoring."""
    return jsonify({'status': 'healthy', 'version': __version__}), 200


@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages."""
    # Check query limit
    current_count = get_query_count()
    if current_count >= MAX_QUERIES_PER_SESSION:
        return jsonify({
            'error': 'limit_reached',
            'message': f'You have reached the maximum of {MAX_QUERIES_PER_SESSION} questions for this session.',
            'query_count': current_count,
            'max_queries': MAX_QUERIES_PER_SESSION
        }), 429

    # Get and validate input
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    # Sanitize input
    user_message = sanitize_input(user_message)
    if not user_message:
        return jsonify({'error': 'Invalid message'}), 400

    # Check length after sanitization
    if len(user_message) > MAX_QUERY_LENGTH:
        return jsonify({
            'error': 'Message too long',
            'max_length': MAX_QUERY_LENGTH
        }), 400

    try:
        # Load persona (re-read each time for hot-swapping)
        persona = load_persona()

        # Add user message to history
        add_to_conversation('user', user_message)

        # Build messages for API call
        messages = [{'role': 'system', 'content': persona}]
        messages.extend(get_conversation_history())

        # Call OpenAI API
        client = get_openai_client()
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )

        assistant_message = response.choices[0].message.content

        # Log the interaction
        log_interaction(QUERY_LOG_PATH, get_session_id(), user_message, assistant_message)

        # Add assistant response to history
        add_to_conversation('assistant', assistant_message)

        # Increment query count
        new_count = increment_query_count()

        return jsonify({
            'response': assistant_message,
            'query_count': new_count,
            'max_queries': MAX_QUERIES_PER_SESSION,
            'queries_remaining': MAX_QUERIES_PER_SESSION - new_count
        })

    except Exception as e:
        return jsonify({
            'error': 'Failed to get response',
            'message': str(e)
        }), 500


@app.route('/vet', methods=['POST'])
def vet():
    """Evaluate a job description against the persona."""
    # Get and validate input
    data = request.get_json()
    if not data or 'job_description' not in data:
        return jsonify({'error': 'No job description provided'}), 400

    job_description = data.get('job_description', '').strip()
    if not job_description:
        return jsonify({'error': 'Empty job description'}), 400

    # Sanitize input
    job_description = sanitize_job_description(job_description, MAX_JOB_DESCRIPTION_LENGTH)
    if not job_description:
        return jsonify({'error': 'Invalid job description'}), 400

    try:
        # Load persona
        persona = load_persona()

        # Get OpenAI client and evaluate
        client = get_openai_client()
        result = evaluate_job_description(client, job_description, persona)

        return jsonify(asdict(result))

    except Exception as e:
        return jsonify({
            'error': 'Failed to evaluate job description',
            'message': str(e)
        }), 500


@app.route('/status')
def status():
    """Get current session status."""
    return jsonify({
        'query_count': get_query_count(),
        'max_queries': MAX_QUERIES_PER_SESSION,
        'queries_remaining': MAX_QUERIES_PER_SESSION - get_query_count(),
        'version': __version__
    })


@app.route('/reset')
def reset():
    """Admin endpoint to reset session. Requires ADMIN_RESET_KEY."""
    if not ADMIN_RESET_KEY:
        return jsonify({'error': 'Reset endpoint not configured'}), 403

    key = request.args.get('key', '')
    if key != ADMIN_RESET_KEY:
        return jsonify({'error': 'Invalid key'}), 403

    # Clear session data
    old_count = get_query_count()
    session.clear()

    return jsonify({
        'status': 'success',
        'message': 'Session reset successfully',
        'previous_query_count': old_count
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ProfileGPT - Ask Eric AI')
    parser.add_argument('--mode', choices=['local', 'container'], default='local',
                       help='Run mode: local (Flask dev server) or container (for Gunicorn)')
    args = parser.parse_args()

    if args.mode == 'local':
        # Local development mode
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=True, host='0.0.0.0', port=port)
    else:
        # Container mode - just print info, Gunicorn handles the serving
        print("Container mode: Use Gunicorn to run the application")
        print("Example: gunicorn -b 0.0.0.0:5000 app:app")
