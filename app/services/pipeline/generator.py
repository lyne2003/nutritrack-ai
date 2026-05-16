from __future__ import annotations

from typing import Any, Dict, List

from app.services.fatsecret.service import retrieve_two_recipes
from app.services.scaling.structured_scaler import scale_structured_ingredients
from app.services.substitution.step3_engine import run_step3_substitution

# Step 4 (your working OpenAI nutrition)
from app.services.nutrition.llm_nutrition import compute_nutrition_per_serving_with_llm


def generate_two_recipes_full_pipeline(
    ingredients_str: str,
    servings: float,
    diets: List[str] | None = None,
    allergies: List[str] | None = None,
    lab_flags: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Full flow:
      Step 1: FatSecret retrieve 2 recipes
      For each recipe:
        Step 2: scale -> scaled_struct
        Step 3: substitute -> final_ingredients + report
        Step 4: OpenAI nutrition -> per_serving ONLY
    Returns: list of 2 recipe results.
    """
    diets = diets or []
    allergies = allergies or []
    lab_flags = lab_flags or []

    # ----------------------
    # Step 1: Retrieve 2 recipes (FatSecret)
    # ----------------------
    print("📡 [Step 1] Searching FatSecret for:", ingredients_str)
    recipes = retrieve_two_recipes(ingredients_str)
    print(f"📡 [Step 1] Retrieved {len(recipes)} recipe(s):", [r.get("recipe_name") for r in recipes])

    results: List[Dict[str, Any]] = []

    for idx, r in enumerate(recipes, start=1):
        recipe_name = r.get("recipe_name") or ""
        recipe_id = r.get("recipe_id")
        base_servings = r.get("base_servings")
        prep_time_min = r.get("prep_time_min")
        steps = r.get("steps") or []
        ingredients_struct = r.get("ingredients_struct") or []

        print(f"\n🍽️  Processing recipe {idx}/{len(recipes)}: {recipe_name}")

        # ----------------------
        # Step 2: Scale
        # ----------------------
        print(f"📏 [Step 2] Scaling: base_servings={base_servings}, user_servings={servings}")
        scaled = scale_structured_ingredients(
            ingredients_struct=ingredients_struct,
            base_servings=base_servings,
            user_servings=servings,
        )
        print(f"📏 [Step 2] Scaling done. {len(scaled.scaled_struct)} ingredient(s) scaled.")

        # ----------------------
        # Step 3: Substitution
        # ----------------------
        print(f"🔄 [Step 3] Running substitution for {len(scaled.scaled_struct)} ingredient(s)...")
        step3 = run_step3_substitution(
            scaled_struct=scaled.scaled_struct,
            diets=diets,
            allergies=allergies,
            lab_flags=lab_flags,
        )
        final_ingredients = step3.get("final_ingredients") or []
        substitution_report = step3.get("substitution_report") or []
        print(f"🔄 [Step 3] Substitution done. {len(final_ingredients)} final ingredient(s).")
        print(f"🔄 [Step 3] Final ingredients: {final_ingredients}")
        print(f"🔄 [Step 3] Substitution report:")
        for line in substitution_report:
            print(f"   → {line}")

        # ----------------------
        # Step 4: Nutrition (OpenAI) -> ONLY per_serving sent to mobile
        # ----------------------
        print(f"🥗 [Step 4] Calling OpenAI for nutrition estimation...")
        nut = compute_nutrition_per_serving_with_llm(
            final_ingredients=final_ingredients,
            servings=servings,
            recipe_name=recipe_name,
        )
        per_serving = nut.get("per_serving") or {}
        print(f"🥗 [Step 4] Nutrition done. {per_serving.get('calories_kcal')} kcal / "
              f"{per_serving.get('protein_g')}g protein / "
              f"{per_serving.get('carbs_g')}g carbs / "
              f"{per_serving.get('fat_g')}g fat")

        print(f"✅ Recipe {idx} done: {recipe_name}")

        results.append(
            {
                "recipe_id": recipe_id,
                "recipe_name": recipe_name,
                "prep_time_min": prep_time_min,
                "steps": steps,
                "final_ingredients": final_ingredients,
                "substitution_report": substitution_report,
                "nutrition_per_serving": per_serving,
                "user_servings": servings,
            }
        )

    print("\n🏁 Pipeline complete. Returning results.")
    return results
