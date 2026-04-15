import json
from pathlib import Path
from config.settings import NICHE_ROTATION_FILE

NICHE_PRODUCT_MAP = {
    "finance": {
        "product": "eToro",
        "description": "Social trading platform — copy top investors automatically",
        # Commission Factory未登録 → リンクなし（登録後に更新）
        "affiliate_link": "",
        "network": "commission_factory",
    },
    "health": {
        "product": "iHerb",
        "description": "Vitamins & supplements — up to 30% off + free shipping",
        # Commission Factory未登録 → リンクなし（登録後に更新）
        "affiliate_link": "",
        "network": "commission_factory",
    },
    "technology": {
        "product": "Amazon Tech AU",
        "description": "Top-rated tech gadgets with fast AU delivery",
        "affiliate_link": "https://www.amazon.com.au/s?k=tech+gadgets&tag=hiroyama04-22",
        "network": "amazon_associates_au",
    },
    "productivity": {
        "product": "Notion",
        "description": "All-in-one workspace — notes, tasks, databases",
        # Notionアフィリプログラム新規受付停止中 → 別プログラム検討
        "affiliate_link": "",
        "network": "notion",
    },
    "psychology": {
        "product": "Audible",
        "description": "Audiobooks & podcasts — first month free",
        "affiliate_link": "https://www.amazon.com.au/hz/audible/mlp/membership/plus?tag=hiroyama04-22",
        "network": "amazon_associates_au",
    },
}


class NicheSelector:
    def get_next(self) -> tuple[str, dict]:
        niches = list(NICHE_PRODUCT_MAP.keys())
        state_file = Path(NICHE_ROTATION_FILE)
        try:
            state = json.loads(state_file.read_text())
            idx = (state.get("last_idx", -1) + 1) % len(niches)
        except FileNotFoundError:
            idx = 0
        state_file.write_text(json.dumps({"last_idx": idx}))
        niche = niches[idx]
        return niche, NICHE_PRODUCT_MAP[niche]
