import re
import logging

import httpx

from app.config import LLM_SERVICE_URL, LLM_MODEL, LLM_API_KEY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Summarize the following article for a podcast feed description.
Format your response as simple HTML:
- One opening sentence describing the main topic in a <p> tag
- Then a <ul> with 2-4 <li> bullet points for key takeaways
Keep it concise and skimmable. Reply with ONLY the HTML summary, no preamble."""


async def generate_summary(text: str, title: str) -> str:
    """Generate an HTML summary via LLM, falling back to text extraction."""
    if LLM_SERVICE_URL:
        try:
            return await _llm_summary(text, title)
        except Exception as e:
            logger.warning("LLM summary failed, using fallback: %s", e)
    return _fallback_summary(text)


async def _llm_summary(text: str, title: str) -> str:
    truncated = text[:3000]
    headers = {}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{LLM_SERVICE_URL}/v1/chat/completions",
            headers=headers,
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Title: {title}\n\n{truncated}"},
                ],
                "max_tokens": 400,
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return _clean_response(content)


def _clean_response(text: str) -> str:
    """Strip thinking output, keeping only the HTML summary."""
    # Remove <think>...</think> blocks
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Strip "Thinking Process:" style preamble — take content after last occurrence
    # of common thinking markers
    for marker in ['</p>\n<ul>', '</p><ul>']:
        if marker in text:
            # Find the first <p> before this marker
            idx = text.find('<p>')
            if idx >= 0:
                text = text[idx:]
                break
    # If no HTML found, the model dumped plain text thinking — try to salvage
    if '<p>' not in text and '<ul>' not in text:
        # Strip everything before a sentence that looks like a summary
        text = re.sub(r'^.*?(?:Thinking Process|Analyze|Step \d).*?(?:\.\s)', '', text, flags=re.DOTALL)
        # Wrap in basic HTML
        text = f'<p>{text.strip()}</p>'
    # Remove markdown artifacts
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    return text.strip()


def _fallback_summary(text: str) -> str:
    """Extract first 4-5 sentences, wrapped in HTML."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip(), maxsplit=5)
    summary = " ".join(sentences[:5])
    if len(summary) > 800:
        summary = summary[:797] + "..."
    return f"<p>{summary}</p>"
