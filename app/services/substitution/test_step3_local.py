from __future__ import annotations

import json
from app.services.substitution.step3_engine import run_step3_substitution

if __name__ == "__main__":
    payload = [
        {"food_name": "butter", "ingredient_description": "2 tbsp butter", "measurement_description": "tbsp", "scaled_number_of_units": "2"},
        {"food_name": "spaghetti", "ingredient_description": "200 g spaghetti", "measurement_description": "g", "scaled_number_of_units": "200"},
        {"food_name": "chicken breast", "ingredient_description": "1 cup cooked chicken breast", "measurement_description": "cup", "scaled_number_of_units": "1"},
        {"food_name": "soy sauce", "ingredient_description": "1 tbsp soy sauce", "measurement_description": "tbsp", "scaled_number_of_units": "1"},
        {"food_name": "salt", "ingredient_description": "1 tsp salt", "measurement_description": "tsp", "scaled_number_of_units": "1"},
    ]

    res = run_step3_substitution(
        scaled_struct=payload,
        diets=["vegan"],
        allergies=["soy"],
        lab_flags=["LDL_HIGH", "GLUCOSE_HIGH", "CREATININE_HIGH"],
    )

    print(json.dumps(res, ensure_ascii=False, indent=2))
