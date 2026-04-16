import json
import re
from utils import claude_client
from prompts.youtube_prompts import YOUTUBE_SHORTS_PROMPT, YOUTUBE_LONGFORM_PROMPT


class YouTubeGenerator:
    def generate(self, niche: str, product: dict, fmt: str = "shorts") -> dict:
        prompt = YOUTUBE_SHORTS_PROMPT if fmt == "shorts" else YOUTUBE_LONGFORM_PROMPT
        affiliate_link = product.get("affiliate_link", "")
        link_note = f"Affiliate link: {affiliate_link}" if affiliate_link else "No affiliate link — focus on value content"

        user_prompt = f"""Create a YouTube {fmt} script for this affiliate product:

Niche: {niche}
Product: {product['product']}
Description: {product['description']}
{link_note}

Return valid JSON only."""

        raw = claude_client.generate(prompt, user_prompt, max_tokens=2000)
        match = re.search(r'\{[\s\S]*"title"[\s\S]*\}', raw)
        if not match:
            raise ValueError(f"No JSON in response: {raw[:200]}")

        data = json.loads(match.group(0))
        data["niche"]   = niche
        data["product"] = product
        data["format"]  = fmt
        return data
