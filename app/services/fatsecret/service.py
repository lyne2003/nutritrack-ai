# app/services/fatsecret/service.py
from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import settings
from app.services.fatsecret.client import FatSecretClient, FatSecretConfig
from app.services.fatsecret.parser import extract_recipe_ids_from_search, normalize_recipe_get_v2


def get_client() -> FatSecretClient:
    cfg = FatSecretConfig(
        client_id=settings.FATSECRET_CLIENT_ID,
        client_secret=settings.FATSECRET_CLIENT_SECRET,
        token_url=settings.FATSECRET_TOKEN_URL,
        api_base=settings.FATSECRET_API_BASE,
    )
    return FatSecretClient(cfg)


def retrieve_two_recipes(ingredients_str: str) -> List[Dict[str, Any]]:
    """
    Step 1 (Retrieval):
    - recipes.search.v3 using user's ingredients string
      region=United States, recipe_type=main dish, include_images=false
    - take 2 recipe_ids
    - recipe.get.v2 for full details
    - normalize fields we need (no nutrition)
    """
    fs = get_client()

    search = fs.recipes_search_v3(
        search_expression=ingredients_str,
        max_results=20,
        region="United States",
        recipe_type="main dish",
        include_images=False,
        page_number=0,
    )

    ids = extract_recipe_ids_from_search(search, limit=2)

    results: List[Dict[str, Any]] = []
    for rid in ids:
        full = fs.recipe_get_v2(rid)
        results.append(normalize_recipe_get_v2(full))

    return results
