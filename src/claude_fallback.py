import json
import anthropic
from src.config import ANTHROPIC_API_KEY

MODEL = "claude-sonnet-4-20250514"

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_PROMPT = (
    "Extract the total invoice amount from the following text. "
    'Respond with ONLY valid JSON in the format {"amount": number | null}. '
    "Use null if no amount is found.\n\n"
)


def extract_with_claude(text: str) -> float | None:
    try:
        message = _client.messages.create(
            model=MODEL,
            max_tokens=64,
            messages=[{"role": "user", "content": _PROMPT + text}],
            timeout=30,
        )
        raw = message.content[0].text.strip()
        data = json.loads(raw)
        value = data.get("amount")
        if value is None:
            return None
        return float(value)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    except anthropic.APITimeoutError:
        return None
    except anthropic.RateLimitError:
        return None
