from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.services.fatsecret.service import retrieve_two_recipes
from app.services.scaling.structured_scaler import scale_structured_ingredients
from app.services.substitution.step3_engine import run_step3_substitution
from app.services.substitution.step_rewriter import rewrite_steps_with_substitutions
from app.services.nutrition.llm_nutrition import compute_nutrition_per_serving_with_llm


def _sse(event_type: str, payload: Any) -> str:
    """Format a single SSE data line."""
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


async def stream_recipe_pipeline(
    ingredients_str: str,
    servings: float,
    diets: Optional[List[str]] = None,
    allergies: Optional[List[str]] = None,
    lab_flags: Optional[List[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE events as the pipeline progresses.

    Event types:
      - progress  {"message": "..."}
      - done      {"recipe": {...}}
      - error     {"message": "..."}
    """
    diets = diets or []
    allergies = allergies or []
    lab_flags = lab_flags or []

    try:
        # ── Step 1: FatSecret ──────────────────────────────────────────────
        yield _sse("progress", {"message": "🔍 Searching for recipes matching your ingredients..."})

        recipes = retrieve_two_recipes(ingredients_str)

        if not recipes:
            yield _sse("error", {"message": "No recipes found. Please try different ingredients."})
            return

        r = recipes[0]
        recipe_name = r.get("recipe_name") or ""
        recipe_id = r.get("recipe_id")
        base_servings = r.get("base_servings")
        prep_time_min = r.get("prep_time_min")
        steps = r.get("steps") or []
        ingredients_struct = r.get("ingredients_struct") or []

        yield _sse("progress", {"message": f"✅ Found \"{recipe_name}\"! Adjusting quantities for {int(servings)} serving(s)..."})

        # ── Step 2: Scale ──────────────────────────────────────────────────
        print(f"📏 [Step 2] Scaling: base_servings={base_servings}, user_servings={servings}")
        scaled = scale_structured_ingredients(
            ingredients_struct=ingredients_struct,
            base_servings=base_servings,
            user_servings=servings,
        )
        print(f"📏 [Step 2] Scaling done. {len(scaled.scaled_struct)} ingredient(s) scaled.")

        yield _sse("progress", {"message": "🔄 Personalizing ingredients for your diet & health profile..."})

        # ── Step 3: Substitution ───────────────────────────────────────────
        step3 = run_step3_substitution(
            scaled_struct=scaled.scaled_struct,
            diets=diets,
            allergies=allergies,
            lab_flags=lab_flags,
        )
        final_ingredients = step3.get("final_ingredients") or []
        final_struct = step3.get("final_struct") or []
        substitution_report = step3.get("substitution_report") or []

        yield _sse("progress", {"message": "✍️ Updating recipe steps to reflect your personalized ingredients..."})

        # ── Step 3b: Rewrite steps ─────────────────────────────────────────
        steps = rewrite_steps_with_substitutions(
            steps=steps,
            scaled_struct=scaled.scaled_struct,
            final_struct=final_struct,
            recipe_name=recipe_name,
            use_llm_polish=True,
        )

        yield _sse("progress", {"message": "🥗 Calculating nutrition facts per serving..."})

        # ── Step 4: Nutrition ──────────────────────────────────────────────
        nut = compute_nutrition_per_serving_with_llm(
            final_ingredients=final_ingredients,
            servings=servings,
            recipe_name=recipe_name,
        )
        per_serving = nut.get("per_serving") or {}

        # ── Done ───────────────────────────────────────────────────────────
        recipe_result = {
            "recipe_id": recipe_id,
            "recipe_name": recipe_name,
            "prep_time_min": prep_time_min,
            "steps": steps,
            "final_ingredients": final_ingredients,
            "substitution_report": substitution_report,
            "nutrition_per_serving": per_serving,
            "user_servings": servings,
        }

        yield _sse("done", {"recipe": recipe_result})

    except Exception as e:
        yield _sse("error", {"message": f"Something went wrong: {str(e)}"})
