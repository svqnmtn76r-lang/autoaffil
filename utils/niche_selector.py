import json
from pathlib import Path
from config.settings import NICHE_ROTATION_FILE

NICHE_PRODUCT_MAP = {
    "finance": {
        "product": "eToro",
        "description": "Social trading platform — copy top investors automatically",
        "affiliate_link": "https://track.commissionfactory.com/etoro",
        "network": "commission_factory",
    },
    "health": {
        "product": "iHerb",
        "description": "Vitamins & supplements — up to 30% off + free shipping",
        "affiliate_link": "https://track.commissionfactory.com/iherb",
        "network": "commission_factory",
    },
    "technology": {
        "product": "Amazon Tech AU",
        "description": "Top-rated tech gadgets with fast AU delivery",
        "affiliate_link": "https://amzn.to/tech-au",
        "network": "amazon_associates_au",
    },
    "productivity": {
        "product": "Notion",
        "description": "All-in-one workspace — notes, tasks, databases",
        "affiliate_link": "https://notion.so/product",
        "network": "impact",
    },
    "psychology": {
        "product": "Audible",
        "description": "Audiobooks & podcasts — first month free",
        "affiliate_link": "https://amzn.to/audible-au",
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
