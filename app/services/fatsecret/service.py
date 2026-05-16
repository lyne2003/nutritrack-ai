# app/services/fatsecret/service.py
from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import settings
from app.services.fatsecret.client import FatSecretClient, FatSecretConfig
from app.services.fatsecret.parser import extract_recipe_ids_from_search, normalize_recipe_get_v2, score_recipe_by_ingredients


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
    - fetch up to 5 recipe candidates
    - recipe.get.v2 for full details on each
    - score each recipe by how many user ingredients it contains
    - return the top 2 by score
    """
    fs = get_client()

    # Parse user ingredient tokens (e.g. "chicken, broccoli, pasta" -> ["chicken", "broccoli", "pasta"])
    user_tokens = [t.strip() for t in ingredients_str.split(",") if t.strip()]

    print(f"📡 [FatSecret] Calling recipes.search.v3 with: '{ingredients_str}'")
    search = fs.recipes_search_v3(
        search_expression=ingredients_str,
        max_results=20,
        region="United States",
        recipe_type="main dish",
        include_images=False,
        page_number=0,
    )

    # Fetch up to 2 candidate recipe IDs (reduced from 5 to speed up pipeline)
    ids = extract_recipe_ids_from_search(search, limit=5)
    print(f"📡 [FatSecret] Found {len(ids)} candidate recipe ID(s): {ids}")

    # Get full details and score each candidate
    scored: List[tuple] = []
    for rid in ids:
        print(f"📡 [FatSecret] Fetching full details for recipe ID: {rid}")
        full = fs.recipe_get_v2(rid)
        normalized = normalize_recipe_get_v2(full)
        score = score_recipe_by_ingredients(normalized, user_tokens)
        print(f"📡 [FatSecret] Recipe '{normalized.get('recipe_name')}' scored {score}")
        scored.append((score, normalized))

    # Sort by score descending, return top 1 (reduced from 2 to speed up pipeline)
    scored.sort(key=lambda x: x[0], reverse=True)
    top1 = [recipe for _, recipe in scored[:1]]
    print(f"📡 [FatSecret] Top 1 selected: {[r.get('recipe_name') for r in top1]}")
    return top1
