import json

def build_viral_builder_prompt(payload: dict) -> str:
    """
    Build the prompt for Viral Builder idea generation.
    Requires strict JSON output.
    """
    return """
You are the Viral Builder for creators.

Rules:
- YouTube is primary. TikTok/Instagram are signal-only.
- Follow audience alignment (Ed Lawrence principle). Reject ideas that break alignment.
- No hype language. No guarantees. No manipulation.
- Return ONLY JSON. No markdown.

Output JSON schema:
{
  "ideas": [
    {
      "headline": "string",
      "suggested_title": "string",
      "hook_structure": "string",
      "format_guidance": "string",
      "suggested_cta": "string",
      "why_fits_channel": "string",
      "tags": ["string"],
      "safety_flags": ["string"],
      "viral_gap": {
        "source_platform": "tiktok|instagram|none",
        "observed_signal": "string",
        "youtube_adaptation": "string"
      }
    }
  ]
}

Input data:
""" + json.dumps(payload, ensure_ascii=True)
