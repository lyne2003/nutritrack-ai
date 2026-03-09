from __future__ import annotations
from typing import Any, Dict, List


def extract_recipe_ids_from_search(search_json: Dict[str, Any], limit: int = 2) -> List[str]:
    recipes_block = search_json.get("recipes", {})
    recipe_list = recipes_block.get("recipe", []) or []

    ids: List[str] = []
    seen = set()

    for r in recipe_list:
        rid = str(r.get("recipe_id", "")).strip()
        if not rid or rid in seen:
            continue
        seen.add(rid)
        ids.append(rid)
        if len(ids) >= limit:
            break

    return ids


def normalize_recipe_get_v2(recipe_get_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize recipe.get.v2 payload to the exact fields we need for our pipeline.
    We do NOT keep nutrition.
    """
    recipe = recipe_get_json.get("recipe", {}) or {}

    recipe_id = str(recipe.get("recipe_id", "")).strip()
    recipe_name = str(recipe.get("recipe_name", "")).strip()

    base_servings = recipe.get("number_of_servings")  # usually numeric string
    prep_time_min = recipe.get("preparation_time_min") or recipe.get("preparation_time")

    # ingredients: recipe["ingredients"]["ingredient"] list of dicts
    ingredients_block = recipe.get("ingredients", {}) or {}
    ingredients = ingredients_block.get("ingredient", []) or []
    if isinstance(ingredients, dict):
        ingredients = [ingredients]

    ingredients_struct = []
    for ing in ingredients:
        if not isinstance(ing, dict):
            continue
        ingredients_struct.append({
            "food_name": ing.get("food_name"),
            "ingredient_description": ing.get("ingredient_description"),
            "number_of_units": ing.get("number_of_units"),
            "measurement_description": ing.get("measurement_description"),
        })

    # directions/steps
    directions_block = recipe.get("directions", {}) or {}
    steps = directions_block.get("direction", []) or []
    if isinstance(steps, str):
        steps = [steps]

    return {
        "recipe_id": recipe_id,
        "recipe_name": recipe_name,
        "base_servings": base_servings,
        "prep_time_min": prep_time_min,
        "ingredients_struct": ingredients_struct,
        "steps": [str(x).strip() for x in steps if str(x).strip()],
    }
