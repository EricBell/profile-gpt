"""
LLM-based intent classification for pre-filtering out-of-scope queries.

Uses a lightweight OpenAI API call to classify user intent before
the main conversation, saving tokens on obvious refusals.
"""

import random
from openai import OpenAI

# Classification system prompt (designed for prompt caching)
CLASSIFICATION_SYSTEM_PROMPT = """You are a scope classifier for a professional Q&A chatbot about Eric Bell.

Your task: Determine if a user's question is about Eric Bell's professional background.

IN-SCOPE topics (respond "IN_SCOPE"):
- Technical skills, programming languages, tools
- Work history, job roles, career progression
- Notable projects, achievements, accomplishments
- Subject matter expertise (DevOps, infrastructure, etc.)
- Working style, values, leadership approach
- Professional development, learning
- System version queries (asking for the persona/profile version)

OUT-OF-SCOPE topics (respond "OUT_OF_SCOPE"):
- Personal life (family, hobbies, favorite things)
- Unrelated topics (weather, sports, politics, current events)
- Generic AI questions ("what are you", "who made you")
- Off-topic requests (math problems, code generation, translations)
- Hypothetical scenarios not about Eric's experience

Edge cases:
- "What's Eric's favorite X?" → OUT_OF_SCOPE (personal preference)
- "How would Eric approach X?" → IN_SCOPE (professional judgment)
- "Tell me about Eric's experience with X" → IN_SCOPE (work history)
- "What version?" or "What's the version?" → IN_SCOPE (system version query)

Respond with ONLY these exact words:
- "IN_SCOPE" if the question is about Eric's professional background
- "OUT_OF_SCOPE" if it's anything else

Do not explain. Do not add punctuation. Just the classification."""

# Rotating refusal responses (professional but approachable)
REFUSAL_RESPONSES = [
    "I'm focused on Eric's professional background. Ask me about his experience, projects, or technical skills!",
    "That's outside my scope, but I can help with questions about Eric's work history, expertise, or professional values.",
    "I only discuss Eric's professional life. Try asking about his technical background or notable projects!",
    "I specialize in Eric's professional profile. Ask about his technical expertise, work experience, or how he approaches problems.",
    "Not my area—I'm here for Eric's career and professional development. What would you like to know about his background?",
    "I focus on Eric's professional side. Happy to discuss his skills, projects, or working style!",
    "That's beyond my scope. I can tell you about Eric's technical experience, leadership approach, or career highlights.",
]


def classify_intent(client: OpenAI, user_message: str) -> str:
    """
    Classify user intent using a lightweight LLM call.

    Args:
        client: OpenAI client instance
        user_message: User's question

    Returns:
        "IN_SCOPE" or "OUT_OF_SCOPE"

    Raises:
        Exception: If classification fails (caller should handle gracefully)
    """
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': CLASSIFICATION_SYSTEM_PROMPT},
            {'role': 'user', 'content': user_message}
        ],
        max_tokens=10,
        temperature=0  # Deterministic classification
    )

    classification = response.choices[0].message.content.strip().upper()

    # Normalize variations (in case LLM adds punctuation)
    if 'IN_SCOPE' in classification or 'IN SCOPE' in classification:
        return 'IN_SCOPE'
    elif 'OUT_OF_SCOPE' in classification or 'OUT SCOPE' in classification:
        return 'OUT_OF_SCOPE'
    else:
        # Unexpected response - default to IN_SCOPE (safe default)
        return 'IN_SCOPE'


def get_refusal_response() -> str:
    """
    Return a random refusal response from the pool.

    Provides variation to avoid robotic repetition.

    Returns:
        Randomly selected refusal message
    """
    return random.choice(REFUSAL_RESPONSES)
