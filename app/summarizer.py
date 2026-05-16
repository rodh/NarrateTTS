import re
import logging

import httpx

from app.config import LLM_SERVICE_URL, LLM_MODEL

logger = logging.getLogger(__name__)


async def generate_summary(text: str, title: str) -> str:
    """Generate a 1-2 sentence summary via LLM, falling back to text extraction."""
    if LLM_SERVICE_URL:
        try:
            return await _llm_summary(text, title)
        except Exception as e:
            logger.warning("LLM summary failed, using fallback: %s", e)
    return _fallback_summary(text)


async def _llm_summary(text: str, title: str) -> str:
    truncated = text[:3000]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{LLM_SERVICE_URL}/v1/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Write a brief summary of this article for a podcast feed description. Include the main topic and 2-3 key points or takeaways. Keep it to a short paragraph — skimmable at a glance but enough to know what the article covers. No bullet points.",
                    },
                    {
                        "role": "user",
                        "content": f"Title: {title}\n\n{truncated}",
                    },
                ],
                "max_tokens": 300,
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


def _fallback_summary(text: str) -> str:
    """Extract first 4-5 sentences, capped at 800 chars."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip(), maxsplit=5)
    summary = " ".join(sentences[:5])
    if len(summary) > 800:
        summary = summary[:797] + "..."
    return summary
