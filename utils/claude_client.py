import os
import json
import urllib.request
import urllib.error

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL      = "claude-haiku-4-5-20251001"
SONNET_MODEL       = "claude-sonnet-4-6"


def _call(model: str, system: str, user: str, max_tokens: int) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()

    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Claude API {e.code}: {e.read().decode()}")


def generate(system: str, user: str, max_tokens: int = 1500) -> str:
    """Haiku — コスト重視（記事生成・SNSコピー）"""
    return _call(DEFAULT_MODEL, system, user, max_tokens)


def generate_sonnet(system: str, user: str, max_tokens: int = 2000) -> str:
    """Sonnet — 品質重視（重要コンテンツ）"""
    return _call(SONNET_MODEL, system, user, max_tokens)
