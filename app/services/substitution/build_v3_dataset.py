import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "data" / "substitution_rules_v3.json"


def build() -> dict:
    # ----------------------------
    # Categories (locked)
    # ----------------------------
    categories = {
        "grain_wheat_pasta_noodles": {"label": "Wheat pasta & noodles", "examples": ["pasta", "spaghetti", "penne", "tagliatelle", "noodles", "macaroni"]},
        "grain_wheat_bread_wraps": {"label": "Bread & wraps", "examples": ["bread", "bun", "pita", "tortilla", "wrap", "bagel"]},
        "grain_wheat_flour_baking": {"label": "Wheat flour & baking", "examples": ["flour", "wheat flour", "breadcrumbs", "cake mix", "dough"]},
        "grain_rice": {"label": "Rice", "examples": ["rice", "white rice", "brown rice"]},
        "grain_corn": {"label": "Corn products", "examples": ["cornmeal", "polenta", "corn tortilla"]},
        "grain_oats": {"label": "Oats", "examples": ["oats", "oatmeal"]},
        "grain_other_gluten": {"label": "Other gluten grains", "examples": ["barley", "rye", "bulgur", "couscous", "semolina"]},

        "grain_gluten_free_pasta_noodles": {"label": "Gluten-free pasta & noodles", "examples": ["gluten-free pasta", "rice noodles", "lentil pasta", "corn pasta"]},
        "grain_gluten_free_bread_wraps": {"label": "Gluten-free bread & wraps", "examples": ["gluten-free bread", "gluten-free wrap"]},
        "grain_gluten_free_flour_baking": {"label": "Gluten-free flour & baking", "examples": ["gluten-free flour", "rice flour", "tapioca flour"]},

        "starch_potato": {"label": "Potato", "examples": ["potato", "fries", "mashed potato"]},
        "starch_starchy_veg": {"label": "Starchy vegetables", "examples": ["peas", "corn kernels"]},

        "protein_poultry": {"label": "Poultry", "examples": ["chicken", "turkey", "chicken breast"]},
        "protein_red_meat": {"label": "Red meat", "examples": ["beef", "lamb"]},
        "protein_processed_meat": {"label": "Processed meat", "examples": ["bacon", "sausage", "deli meat"]},
        "protein_fish_seafood": {"label": "Fish & seafood", "examples": ["fish", "salmon", "tuna", "shrimp"]},
        "protein_eggs": {"label": "Eggs", "examples": ["egg", "egg whites", "whole egg"]},
        "protein_organs": {"label": "Organ meats", "examples": ["liver"]},

        "protein_soy": {"label": "Soy protein", "examples": ["tofu", "edamame", "soy milk", "miso"]},
        "protein_legumes": {"label": "Legumes", "examples": ["beans", "lentils", "chickpeas"]},
        "protein_nuts_tree": {"label": "Tree nuts", "examples": ["almond", "walnut", "cashew"]},
        "protein_peanut": {"label": "Peanuts", "examples": ["peanut", "peanut butter"]},
        "protein_seeds_sesame": {"label": "Sesame", "examples": ["sesame", "tahini"]},
        "protein_seeds_other": {"label": "Other seeds", "examples": ["chia", "flax", "pumpkin seeds", "sunflower seeds"]},

        "dairy_milk_cream": {"label": "Milk & cream", "examples": ["milk", "cream", "half-and-half"]},
        "dairy_cheese": {"label": "Cheese", "examples": ["parmesan", "mozzarella", "cheddar"]},
        "dairy_butter_ghee": {"label": "Butter & ghee", "examples": ["butter", "ghee"]},
        "dairy_yogurt": {"label": "Yogurt", "examples": ["yogurt", "labneh"]},

        "dairy_alt_plant_milk": {"label": "Plant milk", "examples": ["unsweetened coconut milk", "almond milk", "oat milk"]},
        "dairy_alt_vegan_cheese": {"label": "Vegan cheese", "examples": ["vegan cheese"]},
        "dairy_alt_vegan_butter": {"label": "Vegan butter", "examples": ["vegan butter"]},

        "fat_oils": {"label": "Oils", "examples": ["olive oil", "vegetable oil", "canola oil"]},
        "sodium_salt_and_broth": {"label": "Salt & broth", "examples": ["salt", "stock cube", "bouillon", "broth concentrate"]},
        "sauce_condiment_high_sodium": {"label": "High-sodium sauces", "examples": ["soy sauce", "teriyaki", "ketchup", "ready-made sauces"]},
        "sugar_sweeteners": {"label": "Sugar & sweeteners", "examples": ["sugar", "honey", "syrup"]},

        "veg_nonstarchy": {"label": "Non-starchy vegetables", "examples": ["broccoli", "spinach", "zucchini", "mushrooms"]},
        "veg_aromatics": {"label": "Aromatics", "examples": ["onion", "garlic"]},
        "fruit_general": {"label": "Fruits", "examples": ["tomato", "lemon", "berries"]},
        "spices_herbs": {"label": "Spices & herbs", "examples": ["paprika", "pepper", "ginger", "cayenne", "parsley"]},

        "other_unknown": {"label": "Other / unknown", "examples": ["ingredient", "seasoning mix", "product"]},
    }

    # ----------------------------
    # Supported constraints (locked)
    # ----------------------------
    supported = {
        "diets": ["vegetarian", "vegan", "high_protein", "low_carb", "gluten_free", "low_sodium", "low_fat", "halal"],
        "allergies": ["wheat_gluten", "dairy", "egg", "fish", "soy", "tree_nut", "peanut", "sesame"],
        "labs": ["LDL_HIGH", "HDL_LOW", "TRIGLYCERIDES_HIGH", "GLUCOSE_HIGH", "CREATININE_HIGH"],
    }

    # ----------------------------
    # Rule helpers
    # ----------------------------
    def sub(to_cat: str, name: str, reason: str, policy=None, conditional_substitutes=None):
        out = {
            "action": "substitute",
            "to_category": to_cat,
            "substitute_name": name,
            "amount_policy": policy or {"type": "keep_same"},
            "reason_user": reason,
        }
        if conditional_substitutes:
            out["conditional_substitutes"] = conditional_substitutes
        return out

    def reduce(ratio: float, reason: str):
        return {
            "action": "reduce_amount",
            "reduce_ratio": ratio,
            "amount_policy": {"type": "multiplier", "value": ratio},
            "reason_user": reason,
        }

    def inc(ratio: float, reason: str):
        return {
            "action": "increase_amount",
            "increase_ratio": ratio,
            "reason_user": reason,
        }

    # ----------------------------
    # Category rules
    # ----------------------------
    category_rules = {
        # GLUTEN (allergy/diet) rules
        "grain_wheat_pasta_noodles": {
            "allergies": {"wheat_gluten": sub("grain_gluten_free_pasta_noodles", "gluten-free pasta", "it contains gluten")},
            "diets": {"gluten_free": sub("grain_gluten_free_pasta_noodles", "gluten-free pasta", "to avoid gluten")},
            "labs": {
  "GLUCOSE_HIGH": reduce(0.75, "to reduce refined carbs and support blood sugar"),
  "TRIGLYCERIDES_HIGH": reduce(0.75, "to reduce refined carbs and support triglycerides"),
},

            "diets_soft": {"low_carb": sub("veg_nonstarchy", "zucchini noodles", "to lower carbs")},
        },
        "grain_wheat_bread_wraps": {
            "allergies": {"wheat_gluten": sub("grain_gluten_free_bread_wraps", "gluten-free wrap", "it contains gluten")},
            "diets": {"gluten_free": sub("grain_gluten_free_bread_wraps", "gluten-free wrap", "to avoid gluten")},
            "labs": {
                "GLUCOSE_HIGH": sub("veg_nonstarchy", "lettuce wraps", "to reduce refined carbs and support blood sugar"),
                "TRIGLYCERIDES_HIGH": sub("veg_nonstarchy", "lettuce wraps", "to reduce refined carbs and support triglycerides"),
            },
            "diets_soft": {"low_carb": sub("veg_nonstarchy", "lettuce wraps", "to lower carbs")},
        },
        "grain_wheat_flour_baking": {
            "allergies": {"wheat_gluten": sub("grain_gluten_free_flour_baking", "gluten-free flour blend", "it contains gluten")},
            "diets": {"gluten_free": sub("grain_gluten_free_flour_baking", "gluten-free flour blend", "to avoid gluten")},
            "labs": {"GLUCOSE_HIGH": reduce(0.75, "to reduce refined carbs and support blood sugar")},
            "diets_soft": {"low_carb": reduce(0.75, "to reduce carbs")},
        },
        "grain_other_gluten": {
            "allergies": {"wheat_gluten": sub("grain_gluten_free_pasta_noodles", "rice noodles", "it contains gluten grains")},
            "diets": {"gluten_free": sub("grain_gluten_free_pasta_noodles", "rice noodles", "to avoid gluten grains")},
            "labs": {"GLUCOSE_HIGH": reduce(0.75, "to reduce carbohydrate impact for blood sugar")},
            "diets_soft": {"low_carb": reduce(0.75, "to lower carbs")},
        },

        # DAIRY
        "dairy_butter_ghee": {
            "allergies": {"dairy": sub("fat_oils", "olive oil", "it contains dairy", {"type": "multiplier", "value": 0.75})},
            "labs": {"LDL_HIGH": sub("fat_oils", "olive oil", "to reduce saturated fat for LDL control", {"type": "multiplier", "value": 0.75})},
            "diets_soft": {"low_fat": reduce(0.75, "to lower added fat")},
            "diets": {"vegan": sub("dairy_alt_vegan_butter", "vegan butter", "to keep the recipe vegan")},
        },
        "dairy_milk_cream": {
            "allergies": {"dairy": sub("dairy_alt_plant_milk", "unsweetened plant milk", "it contains dairy")},
            "labs": {"LDL_HIGH": sub("dairy_alt_plant_milk", "unsweetened plant milk", "to reduce saturated fat for LDL control")},
            "diets": {"vegan": sub("dairy_alt_plant_milk", "unsweetened plant milk", "to keep the recipe vegan")},
            "diets_soft": {"low_fat": sub("dairy_alt_plant_milk", "unsweetened plant milk", "to reduce fat")},
        },
        "dairy_yogurt": {
            "allergies": {"dairy": sub("dairy_alt_plant_milk", "coconut yogurt (unsweetened)", "it contains dairy")},
            "diets": {"vegan": sub("dairy_alt_plant_milk", "coconut yogurt (unsweetened)", "to keep the recipe vegan")},
            "labs": {"LDL_HIGH": sub("dairy_alt_plant_milk", "coconut yogurt (unsweetened)", "to reduce saturated fat for LDL control")},
        },
        "dairy_cheese": {
            "allergies": {"dairy": sub("dairy_alt_vegan_cheese", "vegan cheese", "it contains dairy")},
            "diets": {"vegan": sub("dairy_alt_vegan_cheese", "vegan cheese", "to keep the recipe vegan")},
            "labs": {"LDL_HIGH": sub("dairy_alt_vegan_cheese", "vegan cheese", "to reduce saturated fat for LDL control")},
            "diets_soft": {"low_fat": reduce(0.75, "to reduce high-fat cheese contribution")},
        },

        # EGGS
        "protein_eggs": {
            "allergies": {"egg": sub("protein_legumes", "flax egg (ground flax + water)", "it contains egg")},
            "diets": {"vegan": sub("protein_legumes", "flax egg (ground flax + water)", "to keep the recipe vegan")},
            "labs": {"LDL_HIGH": sub("protein_legumes", "flax egg (ground flax + water)", "to reduce cholesterol impact for LDL control")},
        },

        # FISH/SEAFOOD
        "protein_fish_seafood": {
            "allergies": {"fish": sub("protein_legumes", "cooked chickpeas", "it contains fish/seafood")},
            "diets": {
                "vegan": sub("protein_legumes", "cooked chickpeas", "to keep the recipe vegan"),
                "vegetarian": sub("protein_legumes", "cooked chickpeas", "to keep the recipe vegetarian"),
            },
            "labs": {"HDL_LOW": inc(0.20, "fish is generally supportive for healthy fats; increased slightly to support HDL")},
        },

        # POULTRY (fixed)
        "protein_poultry": {
            "diets": {
                "vegan": sub(
                    "protein_soy",
                    "tofu",
                    "to keep the recipe vegan",
                    conditional_substitutes={
                        "soy": {"to_category": "protein_legumes", "substitute_name": "cooked lentils"}
                    },
                ),
                "vegetarian": sub(
                    "protein_soy",
                    "tofu",
                    "to keep the recipe vegetarian",
                    conditional_substitutes={
                        "soy": {"to_category": "protein_legumes", "substitute_name": "cooked lentils"}
                    },
                ),
            },
            "labs": {"CREATININE_HIGH": reduce(0.75, "to be conservative with protein for kidney-related constraints")},
            "diets_soft": {"high_protein": inc(0.20, "you requested higher protein")},
        },

        "protein_red_meat": {
            "diets": {
                "vegan": sub("protein_legumes", "cooked lentils", "to keep the recipe vegan"),
                "vegetarian": sub("protein_legumes", "cooked lentils", "to keep the recipe vegetarian"),
                "halal": sub("protein_poultry", "halal-certified chicken", "to ensure halal-friendly protein"),
            },
            "labs": {
                "LDL_HIGH": sub("protein_poultry", "chicken breast", "to reduce saturated fat for LDL control"),
                "CREATININE_HIGH": reduce(0.75, "to be conservative with protein for kidney-related constraints"),
            },
        },

        "protein_processed_meat": {
            "diets": {
                "vegan": sub("protein_legumes", "cooked lentils", "to keep the recipe vegan"),
                "vegetarian": sub("protein_legumes", "cooked lentils", "to keep the recipe vegetarian"),
                "halal": sub("protein_poultry", "halal-certified turkey slices", "processed meat may not be halal-safe"),
            },
            "labs": {
                "LDL_HIGH": sub("protein_poultry", "chicken breast", "to reduce saturated fat for LDL control"),
                "TRIGLYCERIDES_HIGH": reduce(0.75, "processed meats can worsen lipid profile; reduced portion"),
                "CREATININE_HIGH": reduce(0.75, "to be conservative with protein for kidney-related constraints"),
            },
            "diets_soft": {"low_sodium": sub("protein_poultry", "fresh chicken breast", "processed meats are often high sodium")},
        },

        "protein_organs": {
            "diets": {
                "vegan": sub("protein_legumes", "cooked lentils", "to keep the recipe vegan"),
                "vegetarian": sub("protein_legumes", "cooked lentils", "to keep the recipe vegetarian"),
            },
            "labs": {"LDL_HIGH": sub("protein_poultry", "chicken breast", "to reduce cholesterol impact for LDL control")},
        },

        # SOY allergy
        "protein_soy": {"allergies": {"soy": sub("protein_legumes", "cooked lentils", "it contains soy")}},

        # NUT / PEANUT / SESAME allergy
        "protein_nuts_tree": {"allergies": {"tree_nut": sub("protein_seeds_other", "pumpkin seeds", "it contains tree nuts")}},
        "protein_peanut": {"allergies": {"peanut": sub("protein_seeds_other", "sunflower seed butter", "it contains peanuts")}},
        "protein_seeds_sesame": {"allergies": {"sesame": sub("protein_seeds_other", "pumpkin seeds", "it contains sesame")}},

        # LOW SODIUM + kidney sodium rules
        "sodium_salt_and_broth": {
            "labs": {"CREATININE_HIGH": sub("spices_herbs", "salt-free herb blend", "to reduce sodium for kidney-related constraints")},
            "diets_soft": {"low_sodium": sub("spices_herbs", "salt-free herb blend", "to reduce sodium")},
        },

        # HIGH SODIUM SAUCES
        "sauce_condiment_high_sodium": {
            "allergies": {
                # ✅ wheat/gluten -> tamari, BUT if soy allergy exists too -> go soy-free
                "wheat_gluten": sub(
                    "sauce_condiment_high_sodium",
                    "tamari (gluten-free soy sauce)",
                    "it may contain gluten",
                    conditional_substitutes={
                        "soy": {"to_category": "spices_herbs", "substitute_name": "lemon juice + garlic-free herb mix"}
                    },
                ),
                "soy": sub("spices_herbs", "lemon juice + garlic-free herb mix", "it contains soy"),
            },
            "labs": {"CREATININE_HIGH": sub("spices_herbs", "lemon juice + herb mix", "to reduce sodium for kidney-related constraints")},
            "diets_soft": {"low_sodium": sub("spices_herbs", "lemon juice + herb mix", "to reduce sodium")},
        },

        # SUGAR + glucose/triglycerides rules
        "sugar_sweeteners": {
            "labs": {
                "GLUCOSE_HIGH": sub("fruit_general", "berries (small amount)", "to reduce added sugar for blood sugar control"),
                "TRIGLYCERIDES_HIGH": reduce(0.50, "to reduce added sugar for triglycerides control"),
            },
            "diets_soft": {"low_carb": reduce(0.50, "to reduce carbs/sugar")},
        },

        # CARB-heavy categories
        "grain_rice": {
            "labs": {
                "GLUCOSE_HIGH": sub("veg_nonstarchy", "cauliflower rice", "to reduce carbohydrate impact for blood sugar"),
                "TRIGLYCERIDES_HIGH": sub("veg_nonstarchy", "cauliflower rice", "to reduce refined carbs for triglycerides"),
            },
            "diets_soft": {"low_carb": sub("veg_nonstarchy", "cauliflower rice", "to lower carbs")},
        },
        "starch_potato": {
            "labs": {
                "GLUCOSE_HIGH": sub("veg_nonstarchy", "cauliflower mash", "to reduce high-GI starch impact for blood sugar"),
                "TRIGLYCERIDES_HIGH": reduce(0.75, "to reduce starchy portion for triglycerides"),
            },
            "diets_soft": {"low_carb": sub("veg_nonstarchy", "cauliflower mash", "to lower carbs")},
        },
        "starch_starchy_veg": {
            "labs": {"GLUCOSE_HIGH": reduce(0.75, "to reduce starchy portion for blood sugar")},
            "diets_soft": {"low_carb": reduce(0.75, "to reduce carbs")},
        },
    }

    doc = {
        "version": "3.0",
        "constraint_priority": ["allergies", "halal", "diet_bans", "labs", "diet_prefs"],
        "supported": supported,
        "categories": categories,
        "category_rules": category_rules,
        "defaults": {
            "report_prefix": "[Step3]",
            "no_rule_behavior": "keep",
            "llm_fallback_allowed": True,
            "llm_fallback_model": "gpt-4.1-mini",
        },
    }
    return doc


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = build()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Built v3 dataset: {OUT} with {len(data['categories'])} categories")


if __name__ == "__main__":
    main()
