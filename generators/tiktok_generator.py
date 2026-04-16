import json
import re
from utils import claude_client
from prompts.tiktok_prompts import TIKTOK_SYSTEM_PROMPT


class TikTokGenerator:
    def generate(self, niche: str, product: dict) -> dict:
        affiliate_link = product.get("affiliate_link", "")
        link_note = f"Affiliate link: {affiliate_link}" if affiliate_link else "No affiliate link — focus on value"

        user_prompt = f"""Create a viral TikTok video script for this affiliate product:

Niche: {niche}
Product: {product['product']}
Description: {product['description']}
{link_note}

Return valid JSON only."""

        raw = claude_client.generate(TIKTOK_SYSTEM_PROMPT, user_prompt, max_tokens=1200)
        match = re.search(r'\{[\s\S]*"script"[\s\S]*\}', raw)
        if not match:
            raise ValueError(f"No JSON in response: {raw[:200]}")

        data = json.loads(match.group(0))
        data["niche"]   = niche
        data["product"] = product
        return data
