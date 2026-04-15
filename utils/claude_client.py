import os
import json
import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL      = "claude-haiku-4-5-20251001"
SONNET_MODEL       = "claude-sonnet-4-6"


def _call(model: str, system: str, user: str, max_tokens: int) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    resp = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"Claude API {resp.status_code}: {resp.text}")
    return resp.json()["content"][0]["text"]


def generate(system: str, user: str, max_tokens: int = 1500) -> str:
    """Haiku — コスト重視（記事生成・SNSコピー）"""
    return _call(DEFAULT_MODEL, system, user, max_tokens)


def generate_sonnet(system: str, user: str, max_tokens: int = 2000) -> str:
    """Sonnet — 品質重視（重要コンテンツ）"""
    return _call(SONNET_MODEL, system, user, max_tokens)
