import json
from utils import claude_client
from prompts.x_prompts import X_SYSTEM_PROMPT


class XGenerator:
    def generate(self, niche: str, product: dict) -> dict:
        has_link = bool(product.get("affiliate_link", ""))
        link_instruction = (
            f"Section 2: reply with affiliate link + CTA\nAffiliate link: {product['affiliate_link']}"
            if has_link else
            "Section 2: leave blank (write only '---')"
        )
        user_prompt = f"""Create a viral X post for this affiliate product:

Niche: {niche}
Product: {product['product']}
Description: {product['description']}

Return exactly 3 sections separated by ---
Section 1: main post (no link, under 280 chars)
{link_instruction}
Section 3: engagement question reply"""

        raw = claude_client.generate(X_SYSTEM_PROMPT, user_prompt, max_tokens=800)
        parts = [p.strip() for p in raw.split("---")]

        return {
            "main_post":        parts[0] if len(parts) > 0 else raw,
            "link_reply":       parts[1] if len(parts) > 1 else "",
            "engagement_reply": parts[2] if len(parts) > 2 else "",
            "niche":            niche,
            "product":          product,
        }
