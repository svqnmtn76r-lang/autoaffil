import json
import re
from utils import claude_client
from prompts.medium_prompts import MEDIUM_SYSTEM_PROMPT


class MediumGenerator:
    def generate(self, niche: str, product: dict) -> dict:
        user_prompt = f"""Write a Medium article for this niche and affiliate product:

Niche: {niche}
Product: {product['product']}
Description: {product['description']}
Affiliate link: {product['affiliate_link']}

Write a practical, specific article that naturally weaves in the product.
Return valid JSON only."""

        raw = claude_client.generate(MEDIUM_SYSTEM_PROMPT, user_prompt, max_tokens=3000)

        # JSON抽出
        match = re.search(r'\{[\s\S]*"title"[\s\S]*\}', raw)
        if not match:
            raise ValueError(f"No JSON in Claude response: {raw[:200]}")

        data = json.loads(match.group(0))
        data["niche"]   = niche
        data["product"] = product
        return data
