import argparse
import os
import re
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
MAX_QUERIES_PER_SESSION = int(os.environ.get('MAX_QUERIES_PER_SESSION', 20))
MAX_QUERY_LENGTH = int(os.environ.get('MAX_QUERY_LENGTH', 500))
PERSONA_FILE_PATH = os.environ.get('PERSONA_FILE_PATH', './persona.txt')

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


@app.route('/')
def index():
    """Render the chat interface."""
    return render_template('index.html',
                         query_count=get_query_count(),
                         max_queries=MAX_QUERIES_PER_SESSION)


@app.route('/health')
def health():
    """Health check endpoint for container monitoring."""
    return jsonify({'status': 'healthy'}), 200


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


@app.route('/status')
def status():
    """Get current session status."""
    return jsonify({
        'query_count': get_query_count(),
        'max_queries': MAX_QUERIES_PER_SESSION,
        'queries_remaining': MAX_QUERIES_PER_SESSION - get_query_count()
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
