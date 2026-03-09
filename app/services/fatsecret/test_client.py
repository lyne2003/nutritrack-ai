import json

from app.core.config import settings
from app.services.fatsecret.client import FatSecretClient, FatSecretConfig

if __name__ == "__main__":
    cfg = FatSecretConfig(
        client_id=settings.FATSECRET_CLIENT_ID,
        client_secret=settings.FATSECRET_CLIENT_SECRET,
        token_url=settings.FATSECRET_TOKEN_URL,
        api_base=settings.FATSECRET_API_BASE,
    )
    fs = FatSecretClient(cfg)

    res = fs.recipes_search_v3("broccoli, tomato, pasta", max_results=5)
    print("TOP KEYS:", res.keys())

    # Print a compact preview of the recipes part so we can see where IDs live
    print(json.dumps(res["recipes"], indent=2)[:2000])
