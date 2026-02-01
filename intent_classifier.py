# Copyright Polymorph Corporation (2026)

"""
LLM-based intent classification for pre-filtering out-of-scope queries.

Uses a lightweight OpenAI API call to classify user intent before
the main conversation, saving tokens on obvious refusals.
"""

import logging
import random
import re
from openai import OpenAI


def extract_company_names(persona_file_path: str) -> list[str]:
    """
    Extract company/organization names from persona.txt WORK HISTORY section.

    Args:
        persona_file_path: Path to persona.txt file

    Returns:
        List of company names (e.g., ["Polymorph Corporation", "Twitter", "Plymouth Rock Assurance"])
    """
    try:
        with open(persona_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        companies = []
        in_work_history = False

        for line in lines:
            # Check if we're entering WORK HISTORY section
            if '## WORK HISTORY' in line:
                in_work_history = True
                continue

            # Check if we're leaving WORK HISTORY section (next ## heading)
            if in_work_history and line.strip().startswith('##'):
                break

            # Extract company names: **CompanyName** (description)
            # Look for pattern **Text** followed by (description)
            if in_work_history and '**' in line and '(' in line:
                match = re.search(r'\*\*([^*]+)\*\*\s*\(', line)
                if match:
                    company = match.group(1).strip()
                    # Filter out job titles (they contain keywords like /, &, Architect, etc.)
                    job_keywords = ['/', '&', 'Architect', 'Developer', 'Engineer', 'Admin', 'BA', 'Integrator']
                    if not any(keyword in company for keyword in job_keywords):
                        companies.append(company)

        # Also add major clients mentioned in Notable Achievements section
        # Specifically look for Veolia which is a major client
        with open(persona_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract Veolia and other major clients from achievements
        if 'Veolia' in content and 'Veolia' not in companies:
            companies.append('Veolia')

        # Deduplicate and return
        return list(set(companies))

    except Exception as e:
        # Graceful degradation - if extraction fails, return empty list
        logging.warning(f"Failed to extract company names from {persona_file_path}: {e}")
        return []


# Base classification prompt template
_BASE_CLASSIFICATION_PROMPT = """You are a scope classifier for a professional Q&A chatbot about Eric Bell.

Your task: Determine if a user's question is about Eric Bell's professional background.

IN-SCOPE topics (respond "IN_SCOPE"):
- Technical skills, programming languages, tools
- Work history, job roles, career progression
- Notable projects, achievements, accomplishments
- Subject matter expertise (DevOps, infrastructure, etc.)
- Working style, values, leadership approach
- Professional development, learning
- System version queries (asking for the persona/profile version)
- How to use this interface/app (e.g., "How do I use this?", "What is this?", "How does this work?")
- Follow-up questions and clarifications (e.g., "give me examples", "tell me more", "can you elaborate", "what about...", "how so", "such as")

OUT-OF-SCOPE topics (respond "OUT_OF_SCOPE"):
- Personal life (family, hobbies, favorite things)
- Unrelated topics (weather, sports, politics, current events)
- Generic AI questions about the AI itself ("what model are you", "who made you", "what are your capabilities")
- Off-topic requests (math problems, code generation, translations)
- Hypothetical scenarios not about Eric's experience

Edge cases:
- "What's Eric's favorite X?" → OUT_OF_SCOPE (personal preference)
- "How would Eric approach X?" → IN_SCOPE (professional judgment)
- "Tell me about Eric's experience with X" → IN_SCOPE (work history)
- "What version?" or "What's the version?" → IN_SCOPE (system version query)"""


def build_classification_prompt(company_names: list[str]) -> str:
    """
    Build classification system prompt with company context.

    Args:
        company_names: List of companies Eric worked for/with

    Returns:
        System prompt string with company examples
    """
    prompt = _BASE_CLASSIFICATION_PROMPT

    # Add company names section if available
    if company_names:
        prompt += "\n\nKnown companies/organizations Eric worked for (always IN_SCOPE):\n"
        for company in sorted(company_names):
            prompt += f"- {company}\n"
        prompt += "\nAny question mentioning these companies is IN_SCOPE."

    # Add final instructions
    prompt += """

Respond with ONLY these exact words:
- "IN_SCOPE" if the question is about Eric's professional background
- "OUT_OF_SCOPE" if it's anything else

Do not explain. Do not add punctuation. Just the classification."""

    return prompt

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


def classify_intent(client: OpenAI, user_message: str, company_names: list[str] = None) -> str:
    """
    Classify user intent using a lightweight LLM call.

    Args:
        client: OpenAI client instance
        user_message: User's question
        company_names: List of companies Eric worked for (for context)

    Returns:
        "IN_SCOPE" or "OUT_OF_SCOPE"

    Raises:
        Exception: If classification fails (caller should handle gracefully)
    """
    # Build system prompt with company context
    if company_names is None:
        company_names = []
    system_prompt = build_classification_prompt(company_names)

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': system_prompt},
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


def get_warning_response(current_count: int, cutoff: int) -> str:
    """
    Generate warning when approaching OUT_OF_SCOPE cutoff.

    Args:
        current_count: Current out-of-scope question count
        cutoff: Maximum allowed out-of-scope questions

    Returns:
        Warning message string
    """
    remaining = cutoff - current_count

    if remaining <= 0:
        return "You have asked too many off-topic questions. This session has been limited."
    else:
        return "You're straying away from Eric's professional life too much. I'll cut you off if you continue."
