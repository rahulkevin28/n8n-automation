import os
import logging
import time

from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = (2, 5, 10)


def _is_transient_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    return code in {429, 500, 502, 503, 504}

def generate_response(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    from google import genai

    client = genai.Client(api_key=api_key)
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            text = getattr(response, "text", None)
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError("Gemini returned an empty response")
            return text
        except Exception as exc:
            if not _is_transient_error(exc):
                logger.exception("Gemini workflow generation failed with a non-retryable error")
                raise
            if attempt >= MAX_RETRIES:
                logger.exception("Gemini workflow generation retries exhausted")
                raise RuntimeError("Gemini is temporarily unavailable after multiple attempts") from exc
            delay = RETRY_DELAYS[attempt]
            logger.warning("Transient Gemini error; retrying attempt %d/%d in %d seconds", attempt + 1, MAX_RETRIES, delay)
            time.sleep(delay)
