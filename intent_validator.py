"""
Intent validation module for pre-LLM filtering of out-of-scope queries.

This module provides keyword-based classification to catch obviously out-of-scope
questions before they reach the LLM, saving tokens and providing faster responses.

Strategy: Conservative filtering with safe defaults
- Only filter obviously out-of-scope queries
- When uncertain, default to in-scope (let LLM handle it)
- Prefer false negatives over false positives
"""

import random

# Out-of-scope keyword patterns by category
# These are conservative - only catch obviously unrelated questions
OUT_OF_SCOPE_PATTERNS = {
    'generic_ai': [
        'what are you',
        'who are you',
        'what can you do',
        'how do you work',
        'are you real',
        'are you a bot',
        'are you an ai',
        'what is your purpose',
        'what is my name',
        'who am i',
        'do you remember me',
        'can you see me',
    ],
    'unrelated_topics': [
        'weather',
        'forecast',
        'temperature',
        'sports',
        'game score',
        'politics',
        'election',
        'president',
        'cooking',
        'recipe',
        'joke',
        'tell me a joke',
        'funny story',
        'movie',
        'tv show',
        'celebrity',
        'news today',
        'stock market',
        'cryptocurrency',
        'horoscope',
        'zodiac',
        'astrology',
        "what's the date",
        "what's the time",
        'what day is',
        'current date',
        'current time',
        'today date',
        'time now',
    ],
    'personal_life': [
        'family',
        'spouse',
        'children',
        'kids',
        'dating',
        'girlfriend',
        'boyfriend',
        'married',
        'hobbies',
        'favorite food',
        'favorite color',
        'favorite movie',
        'where do you live',
        'home address',
        'phone number',
        'birthday',
        'age',
    ],
    'off_topic_requests': [
        'create app for me',
        'write code for me',
        'debug my code',
        'help me with my',
        'do my homework',
        'write my essay',
        'solve this problem',
        'calculate',
        'translate',
        'define',
        'what does',
        'what is ',
        'math problem',
        'solve equation',
    ],
}

# In-scope keyword signals (indicate Eric-related professional questions)
IN_SCOPE_SIGNALS = [
    'eric',
    'experience',
    'project',
    'work',
    'worked',
    'skill',
    'skills',
    'background',
    'technical',
    'technology',
    'team',
    'leadership',
    'developer',
    'engineer',
    'engineering',
    'career',
    'professional',
    'expertise',
    'role',
    'position',
    'job',
    'company',
    'companies',
    'portfolio',
    'achievement',
    'accomplishment',
]

# Rotating refusal responses (balanced tone - professional but approachable)
REFUSAL_RESPONSES = [
    "I'm focused on Eric's professional background. Ask me about his experience, projects, or technical skills!",
    "That's outside my scope, but I can help with questions about Eric's work history, expertise, or professional values.",
    "I only discuss Eric's professional life. Try asking about his technical background or notable projects!",
    "I specialize in Eric's professional profile. Ask about his technical expertise, work experience, or how he approaches problems.",
    "Not my area—I'm here for Eric's career and professional development. What would you like to know about his background?",
    "I focus on Eric's professional side. Happy to discuss his skills, projects, or working style!",
    "That's beyond my scope. I can tell you about Eric's technical experience, leadership approach, or career highlights.",
]


def _contains_math_expression(message: str) -> bool:
    """Check if message contains obvious math expressions."""
    import re
    # Pattern for basic math: numbers with operators
    # Matches things like "4+2", "what's 2*3", "10-5", "8/2"
    math_pattern = r'\d+\s*[+\-*/×÷]\s*\d+'
    return bool(re.search(math_pattern, message))


def is_likely_in_scope(message: str) -> bool:
    """
    Quick heuristic check if message is likely in-scope for Eric's professional background.

    Args:
        message: User's question/message

    Returns:
        True if likely in-scope (should go to LLM)
        False if likely out-of-scope (should be filtered with canned response)

    Strategy:
        - Default to True (in-scope) when uncertain
        - Only return False for obviously out-of-scope queries
        - Prefer false negatives (missed filters) over false positives (blocked valid questions)
    """
    if not message or len(message.strip()) < 3:
        # Too short to classify - let LLM handle it
        return True

    message_lower = message.lower()

    # Check for math expressions (e.g., "what's 4+2")
    if _contains_math_expression(message):
        return False

    # Check for strong out-of-scope signals
    for category, patterns in OUT_OF_SCOPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in message_lower:
                # Found obvious out-of-scope keyword
                # Double-check: does it also mention Eric/professional terms?
                # If yes, let LLM handle the nuance
                has_in_scope_signal = any(signal in message_lower for signal in IN_SCOPE_SIGNALS)
                if not has_in_scope_signal:
                    # Definitely out-of-scope
                    return False
                # Edge case: mentions both (e.g., "What's Eric's favorite food?")
                # Let LLM handle it for now
                return True

    # No strong out-of-scope signals found
    # Default to in-scope (safe default)
    return True


def get_refusal_response() -> str:
    """
    Return a random refusal response from the pool.

    This provides variation to avoid robotic repetition.

    Returns:
        Randomly selected refusal message
    """
    return random.choice(REFUSAL_RESPONSES)


def get_filter_category(message: str) -> str:
    """
    Identify which category triggered the out-of-scope filter.

    Args:
        message: User's question/message

    Returns:
        Category name (e.g., 'generic_ai', 'unrelated_topics') or 'unknown'

    Note:
        This is for analytics only. Should only be called for messages
        where is_likely_in_scope() returned False.
    """
    message_lower = message.lower()

    # Check for math expressions first
    if _contains_math_expression(message):
        return 'off_topic_requests'

    for category, patterns in OUT_OF_SCOPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in message_lower:
                return category

    return 'unknown'
