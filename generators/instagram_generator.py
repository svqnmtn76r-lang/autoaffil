import json
import re
from utils import claude_client
from prompts.instagram_prompts import INSTAGRAM_SYSTEM_PROMPT


class InstagramGenerator:
    def generate(self, niche: str, product: dict) -> dict:
        user_prompt = f"""Create a viral Instagram post for this affiliate product:

Niche: {niche}
Product: {product['product']}
Description: {product['description']}
Affiliate link: {product['affiliate_link']}

Focus on value-first content that makes people save the post.
Return valid JSON only."""

        raw = claude_client.generate(INSTAGRAM_SYSTEM_PROMPT, user_prompt, max_tokens=1000)

        match = re.search(r'\{[\s\S]*"caption"[\s\S]*\}', raw)
        if not match:
            raise ValueError(f"No JSON in Claude response: {raw[:200]}")

        data = json.loads(match.group(0))
        data["niche"]   = niche
        data["product"] = product
        return data
