"""Job description vetting module for ProfileGPT."""

import json
import re
from dataclasses import dataclass
from typing import List


@dataclass
class VettingResult:
    """Result of job description vetting."""
    overall_score: int
    skills_match: int
    experience_match: int
    role_fit: int
    summary: str
    strengths: List[str]
    gaps: List[str]
    recommendation: str


def sanitize_job_description(job_description: str, max_length: int = 5000) -> str:
    """Sanitize and truncate job description input."""
    if not job_description:
        return ""

    # Strip whitespace
    job_description = job_description.strip()

    # Truncate to max length
    if len(job_description) > max_length:
        job_description = job_description[:max_length]

    # Remove potential injection patterns (similar to chat sanitization)
    patterns_to_remove = [
        r'(?i)ignore\s+(all\s+)?(previous|above|prior)\s+instructions?',
        r'(?i)forget\s+(all\s+)?(previous|above|prior)\s+instructions?',
        r'(?i)disregard\s+(all\s+)?(previous|above|prior)\s+instructions?',
        r'(?i)system\s*:\s*',
    ]

    for pattern in patterns_to_remove:
        job_description = re.sub(pattern, '', job_description)

    return job_description.strip()


def evaluate_job_description(client, job_description: str, persona: str) -> VettingResult:
    """
    Evaluate a job description against the persona using OpenAI.

    Args:
        client: OpenAI client instance
        job_description: The sanitized job description to evaluate
        persona: The persona/background information to evaluate against

    Returns:
        VettingResult with scores and analysis
    """
    system_prompt = """You are a job matching analyst. Your task is to evaluate how well a candidate matches a job description.

You will be given:
1. The candidate's background and experience (persona)
2. A job description

Analyze the match and return a JSON object with the following structure:
{
    "overall_score": <0-100 integer>,
    "skills_match": <0-100 integer>,
    "experience_match": <0-100 integer>,
    "role_fit": <0-100 integer>,
    "summary": "<1-2 sentence summary of the match>",
    "strengths": ["<strength 1>", "<strength 2>", ...],
    "gaps": ["<gap 1>", "<gap 2>", ...],
    "recommendation": "<brief recommendation based on score>"
}

Scoring guidelines:
- skills_match: How well the candidate's technical and soft skills align with requirements
- experience_match: How well the candidate's years and type of experience match
- role_fit: How well the candidate fits the role's responsibilities and culture
- overall_score: Weighted average (skills 40%, experience 30%, role fit 30%)

Score interpretation for recommendation:
- 85-100: Strong Match - Highly qualified candidate
- 70-84: Good Match - Well-suited with minor gaps
- 50-69: Partial Match - Some relevant experience but notable gaps
- 0-49: Limited Match - Significant gaps in qualifications

Return ONLY valid JSON, no other text."""

    user_prompt = f"""## Candidate Background:
{persona}

## Job Description:
{job_description}

Analyze this match and return the JSON result."""

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )

        result_text = response.choices[0].message.content.strip()

        # Try to extract JSON from the response (handle markdown code blocks)
        if result_text.startswith('```'):
            # Remove markdown code block formatting
            result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)

        result_data = json.loads(result_text)

        return VettingResult(
            overall_score=max(0, min(100, int(result_data.get('overall_score', 0)))),
            skills_match=max(0, min(100, int(result_data.get('skills_match', 0)))),
            experience_match=max(0, min(100, int(result_data.get('experience_match', 0)))),
            role_fit=max(0, min(100, int(result_data.get('role_fit', 0)))),
            summary=str(result_data.get('summary', '')),
            strengths=list(result_data.get('strengths', [])),
            gaps=list(result_data.get('gaps', [])),
            recommendation=str(result_data.get('recommendation', ''))
        )

    except json.JSONDecodeError:
        return VettingResult(
            overall_score=0,
            skills_match=0,
            experience_match=0,
            role_fit=0,
            summary="Unable to analyze job description",
            strengths=[],
            gaps=["Analysis failed - please try again"],
            recommendation="Could not complete analysis"
        )
    except Exception as e:
        return VettingResult(
            overall_score=0,
            skills_match=0,
            experience_match=0,
            role_fit=0,
            summary=f"Error during analysis: {str(e)}",
            strengths=[],
            gaps=["Analysis error occurred"],
            recommendation="Please try again later"
        )
