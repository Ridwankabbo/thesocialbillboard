import openai
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_ai_score(description):
    print(f"🔍 Generating AI score for description: {description[:50]}...")

    if not description.strip():
        return 2.0

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert content reviewer.",
                },
                {
                    "role": "user",
                    "content": f"Rate the following YouTube channel's description from 1 to 10 for creativity, originality, and audience engagement:\n\n\"{description}\"\n\nOnly respond with a number.",
                },
            ],
            max_tokens=3,
            temperature=0.5,
        )

        result = response.choices[0].message.content.strip()
        score = float(result)
        return max(1.0, min(score, 10.0))

    except Exception as e:
        print("❌ OpenAI API Exception:", str(e))
        return 7.0
