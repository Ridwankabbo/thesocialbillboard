from openai import OpenAI
from pydantic import json

client = OpenAI()


def build_prompt(transcript, title, context="single_video", session_length = "10 minutes" ):
    return f"""
You are a strict content safety and education analysis engine.

Analyze ONLY the transcript below. Do NOT guess or hallucinate.

VIDEO TITLE:
{title}

CONTEXT:
{context}

TRANSCRIPT:
{transcript}

SESSION LENGTH:
{session_length}

Return ONLY valid JSON in this format:

{{
  "summary": "string",
  "age_rating": "3-5 | 6-8 | 9-11 | 12-14 | 15-16 | 17-18",
  "safety_score": 0-100,
  "creator_score": 0-100,
  "educational_value": 0-100,
  "risk_flags": [
    {{
      "type": "violence | profanity | unsafe_content | etc",
      "severity": "low | medium | high",
      "evidence": "quote from transcript"
    }}
  ],
  "confidence": 0-1
}}

Rules:
- Base everything ONLY on transcript
- If unsure, lower confidence
- Always return valid JSON
"""


def analyze_transcript(transcript_text, title, context="single_video", session_length = "10 minutes"):

    if not transcript_text or len(transcript_text.strip()) < 20:
        return {
            "error": "Transcript too short or empty",
            "confidence": 0
        }

    prompt = build_prompt(transcript_text, title, context, session_length)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    output_text = response.output_text

    # safe JSON parsing (VERY IMPORTANT IN PROD)
    try:
        result = json.loads(output_text)
    except Exception:
        result = {
            "raw_output": output_text,
            "error": "Invalid JSON from model",
            "confidence": 0
        }

    return result