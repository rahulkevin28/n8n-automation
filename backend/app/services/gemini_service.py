import os
import logging

from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)

def generate_response(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    from google import genai

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Gemini returned an empty response")
        return text
    except Exception:
        logger.exception("Gemini workflow generation request failed")
        raise
