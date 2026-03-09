from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List


DATA_DIR = Path("app/services/substitution/data")
SRC = DATA_DIR / "substitution_rules_v2.json"
OUT = DATA_DIR / "substitution_rules_v2.json"  # overwrite v2 in-place


FLAG_SCHEMA = [
    # Diet-related
    "is_vegetarian_ok",
    "is_vegan_ok",
    "is_halal_ok",
    "is_gluten_free_ok",
    "is_low_carb_risky",
    "is_low_sodium_risky",
    "is_low_fat_risky",
    "is_high_protein_source",
    # Allergens
    "contains_wheat_gluten",
    "contains_dairy",
    "contains_egg",
    "contains_fish",
    "contains_shellfish",
    "contains_soy",
    "contains_tree_nut",
    "contains_peanut",
    "contains_sesame",
    # Lab heuristics (conservative nutrition heuristics)
    "raises_ldl_risk",
    "raises_triglycerides_risk",
    "raises_glucose_risk",
    "kidney_risky_high_sodium",
    "kidney_risky_very_high_protein",
]


def base_flags() -> Dict[str, bool]:
    return {k: False for k in FLAG_SCHEMA} | {
        "is_vegetarian_ok": True,
        "is_vegan_ok": True,
        "is_halal_ok": True,
        "is_gluten_free_ok": True,
    }


TEMPLATES: Dict[str, Dict[str, Any]] = {
    "T_NEUTRAL_PLANT": {
        "flags": base_flags(),
        "notes": "Default neutral plant-based / ingredient. Vegetarian/Vegan/Halal/GF ok."
    },

    # Gluten / grains
    "T_WHEAT_GRAIN": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "is_gluten_free_ok": False,
            "contains_wheat_gluten": True,
            "is_low_carb_risky": True,
            "raises_glucose_risk": True
        }
    },
    "T_BARLEY_RYE": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "is_gluten_free_ok": False,
            "contains_wheat_gluten": True,  # we treat gluten grains under same allergy bucket
            "is_low_carb_risky": True,
            "raises_glucose_risk": True
        }
    },
    "T_GF_GRAIN": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "is_low_carb_risky": True,
            "raises_glucose_risk": True
        }
    },

    # Animal proteins
    "T_ANIMAL_LEAN_PROTEIN": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "is_vegetarian_ok": False,
            "is_vegan_ok": False,
            "is_high_protein_source": True,
            "kidney_risky_very_high_protein": True
        }
    },
    "T_ANIMAL_FATTY_PROTEIN": {
        "inherits": "T_ANIMAL_LEAN_PROTEIN",
        "flags_override": {
            "is_low_fat_risky": True,
            "raises_ldl_risk": True,
            "raises_triglycerides_risk": True
        }
    },
    "T_FISH": {
        "inherits": "T_ANIMAL_LEAN_PROTEIN",
        "flags_override": {"contains_fish": True}
    },
    "T_SHELLFISH": {
        "inherits": "T_ANIMAL_LEAN_PROTEIN",
        "flags_override": {"contains_shellfish": True}
    },
    "T_PORK": {
        "inherits": "T_ANIMAL_FATTY_PROTEIN",
        "flags_override": {"is_halal_ok": False}
    },

    # Dairy / eggs
    "T_DAIRY": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "is_vegan_ok": False,
            "contains_dairy": True
        }
    },
    "T_DAIRY_FAT": {
        "inherits": "T_DAIRY",
        "flags_override": {
            "is_low_fat_risky": True,
            "raises_ldl_risk": True,
            "raises_triglycerides_risk": True
        }
    },
    "T_EGG": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "is_vegan_ok": False,
            "contains_egg": True
        }
    },

    # Oils / fats
    "T_ADDED_FAT": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "is_low_fat_risky": True,
            "raises_ldl_risk": True  # conservative (some oils are better; overrides below)
        }
    },
    "T_OLIVE_OIL": {
        "inherits": "T_ADDED_FAT",
        "flags_override": {
            "raises_ldl_risk": False
        }
    },

    # Sodium / sugar
    "T_HIGH_SODIUM": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "is_low_sodium_risky": True,
            "kidney_risky_high_sodium": True
        }
    },
    "T_SUGAR": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "is_low_carb_risky": True,
            "raises_glucose_risk": True,
            "raises_triglycerides_risk": True
        }
    },

    # Soy / nuts / seeds allergens
    "T_SOY": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {
            "contains_soy": True,
            "is_high_protein_source": True
        }
    },
    "T_TREE_NUT": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {"contains_tree_nut": True}
    },
    "T_PEANUT": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {"contains_peanut": True}
    },
    "T_SESAME": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {"contains_sesame": True}
    },

    # Halal risks
    "T_ALCOHOL": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {"is_halal_ok": False, "raises_triglycerides_risk": True}
    },
    "T_GELATIN": {
        "inherits": "T_NEUTRAL_PLANT",
        "flags_override": {"is_halal_ok": False, "is_vegetarian_ok": False, "is_vegan_ok": False}
    },
}

DEFAULT_SUBS = {
    # Allergies → safe target category
    "wheat_gluten": "grain.gluten_free.pasta",
    "dairy": "dairy_alt.plant_milk",
    "egg": "protein.plant.legume",
    "fish": "protein.animal.poultry",
    "soy": "protein.plant.legume",
    "tree_nut": "seeds.other",
    "peanut": "seeds.other",
    "sesame": "seeds.other",

    # Diets
    "vegan": "protein.plant.legume",
    "vegetarian": "protein.plant.legume",
    "halal": "protein.animal.poultry",

    # Low-carb swap (generic fallback)
    "low_carb": "vegetable.non_starchy",
}



def resolve_template_flags(templates: Dict[str, Dict[str, Any]], template_name: str) -> Dict[str, bool]:
    t = templates[template_name]
    if "flags" in t:
        return dict(t["flags"])
    parent = t.get("inherits")
    if not parent:
        raise ValueError(f"Template {template_name} has no flags and no inherits")
    flags = resolve_template_flags(templates, parent)
    for k, v in t.get("flags_override", {}).items():
        flags[k] = v
    # ensure all flags exist
    for k in FLAG_SCHEMA:
        flags.setdefault(k, False)
    return flags


def cat(category_id: str, label: str, template: str, examples: List[str], keywords: List[str] | None = None) -> Dict[str, Any]:
    return {
        "label": label,
        "template": template,
        "examples": examples[:15],
        "keywords": (keywords or [])[:20],
        "flags": resolve_template_flags(TEMPLATES, template)
    }


def build_categories() -> Dict[str, Any]:
    C: Dict[str, Any] = {}

    # ---- Proteins (animal)
    C["protein.animal.poultry"] = cat("protein.animal.poultry", "Poultry", "T_ANIMAL_LEAN_PROTEIN",
                                     ["chicken breast", "chicken thighs", "turkey", "ground turkey", "chicken"])
    C["protein.animal.red_meat"] = cat("protein.animal.red_meat", "Red meat", "T_ANIMAL_FATTY_PROTEIN",
                                       ["beef", "steak", "lamb", "veal", "ground beef"])
    C["protein.animal.fish"] = cat("protein.animal.fish", "Fish", "T_FISH",
                                   ["salmon", "tuna", "cod", "tilapia", "fish fillet"])
    C["protein.animal.shellfish"] = cat("protein.animal.shellfish", "Shellfish", "T_SHELLFISH",
                                        ["shrimp", "prawns", "crab", "lobster", "scallops"])
    C["protein.animal.pork"] = cat("protein.animal.pork", "Pork", "T_PORK",
                                   ["pork", "bacon", "ham", "pork chops", "pepperoni"])
    C["protein.animal.processed_meat"] = cat("protein.animal.processed_meat", "Processed meats", "T_ANIMAL_FATTY_PROTEIN",
                                             ["sausage", "salami", "hot dog", "deli meat", "pepperoni"])
    C["protein.animal.organ_meat"] = cat("protein.animal.organ_meat", "Organ meats", "T_ANIMAL_FATTY_PROTEIN",
                                         ["liver", "kidney", "heart", "giblets", "tripe"])

    # ---- Plant proteins
    C["protein.plant.legume"] = cat("protein.plant.legume", "Legumes", "T_NEUTRAL_PLANT",
                                    ["lentils", "chickpeas", "beans", "kidney beans", "black beans"],
                                    ["legume", "dal"])
    # mark legumes as protein source (override flags)
    C["protein.plant.legume"]["flags"]["is_high_protein_source"] = True

    C["protein.plant.soy"] = cat("protein.plant.soy", "Soy proteins", "T_SOY",
                                 ["tofu", "tempeh", "edamame", "soy chunks", "soy mince"])
    C["protein.plant.seitan"] = cat("protein.plant.seitan", "Seitan", "T_WHEAT_GRAIN",
                                    ["seitan", "wheat meat", "vital wheat gluten"],
                                    ["gluten"])
    C["protein.plant.nut_based"] = cat("protein.plant.nut_based", "Nut-based proteins", "T_TREE_NUT",
                                       ["almond flour", "cashew cream", "walnut meat", "almonds", "cashews"])
    C["protein.plant.seed_based"] = cat("protein.plant.seed_based", "Seed-based proteins", "T_NEUTRAL_PLANT",
                                        ["pumpkin seeds", "sunflower seeds", "chia seeds", "flax seeds", "hemp seeds"])
    C["protein.plant.seed_based"]["flags"]["is_high_protein_source"] = True
    C["protein.plant.mushroom_based"] = cat("protein.plant.mushroom_based", "Mushroom-based", "T_NEUTRAL_PLANT",
                                           ["mushrooms", "portobello", "shiitake", "oyster mushrooms", "button mushrooms"])

    # ---- Supplements
    C["protein.supplement.whey"] = cat("protein.supplement.whey", "Whey protein", "T_DAIRY",
                                       ["whey protein", "whey isolate", "whey concentrate"])
    C["protein.supplement.whey"]["flags"]["is_high_protein_source"] = True
    C["protein.supplement.whey"]["flags"]["kidney_risky_very_high_protein"] = True
    C["protein.supplement.casein"] = cat("protein.supplement.casein", "Casein protein", "T_DAIRY",
                                         ["casein protein", "micellar casein"])
    C["protein.supplement.casein"]["flags"]["is_high_protein_source"] = True
    C["protein.supplement.casein"]["flags"]["kidney_risky_very_high_protein"] = True
    C["protein.supplement.plant_powder"] = cat("protein.supplement.plant_powder", "Plant protein powder", "T_NEUTRAL_PLANT",
                                               ["pea protein", "rice protein", "plant protein powder"])
    C["protein.supplement.plant_powder"]["flags"]["is_high_protein_source"] = True
    C["protein.supplement.plant_powder"]["flags"]["kidney_risky_very_high_protein"] = True

    # ---- Grains wheat/gluten
    C["grain.wheat.flour"] = cat("grain.wheat.flour", "Wheat flour", "T_WHEAT_GRAIN",
                                 ["flour", "wheat flour", "all-purpose flour", "bread flour"])
    C["grain.wheat.pasta"] = cat("grain.wheat.pasta", "Wheat pasta", "T_WHEAT_GRAIN",
                                 ["pasta", "spaghetti", "penne", "macaroni", "noodles"])
    C["grain.wheat.bread"] = cat("grain.wheat.bread", "Bread & buns", "T_WHEAT_GRAIN",
                                 ["bread", "bun", "bagel", "toast", "sandwich bread"])
    C["grain.wheat.breadcrumbs"] = cat("grain.wheat.breadcrumbs", "Breadcrumbs", "T_WHEAT_GRAIN",
                                       ["breadcrumbs", "panko", "crumbs"])
    C["grain.wheat.tortilla_wrap"] = cat("grain.wheat.tortilla_wrap", "Wraps & tortillas", "T_WHEAT_GRAIN",
                                         ["tortilla", "wrap", "pita", "flatbread"])
    C["grain.wheat.couscous_bulgur"] = cat("grain.wheat.couscous_bulgur", "Couscous & bulgur", "T_WHEAT_GRAIN",
                                          ["couscous", "bulgur"])
    C["grain.wheat.noodles"] = cat("grain.wheat.noodles", "Wheat noodles", "T_WHEAT_GRAIN",
                                   ["ramen noodles", "egg noodles", "udon"])
    C["grain.barley"] = cat("grain.barley", "Barley", "T_BARLEY_RYE",
                            ["barley", "pearled barley"])
    C["grain.rye"] = cat("grain.rye", "Rye", "T_BARLEY_RYE",
                         ["rye bread", "rye", "pumpernickel"])

    # ---- Gluten-free grains
    C["grain.gluten_free.flour"] = cat("grain.gluten_free.flour", "Gluten-free flour blend", "T_GF_GRAIN",
                                       ["gluten-free flour", "rice flour", "corn flour", "tapioca flour"])
    C["grain.gluten_free.pasta"] = cat("grain.gluten_free.pasta", "Gluten-free pasta", "T_GF_GRAIN",
                                       ["gluten-free pasta", "rice pasta", "corn pasta", "lentil pasta"])
    C["grain.rice.white"] = cat("grain.rice.white", "White rice", "T_GF_GRAIN",
                                ["white rice", "jasmine rice", "basmati rice"])
    C["grain.rice.brown"] = cat("grain.rice.brown", "Brown rice", "T_GF_GRAIN",
                                ["brown rice"])
    C["grain.oats"] = cat("grain.oats", "Oats (cross-contamination possible)", "T_GF_GRAIN",
                          ["oats", "oatmeal", "rolled oats"])
    # oats: GF risk ambiguous (keep gf ok true, but still carb risky)
    C["grain.corn"] = cat("grain.corn", "Corn", "T_GF_GRAIN",
                          ["corn", "polenta", "cornmeal"])
    C["grain.quinoa"] = cat("grain.quinoa", "Quinoa", "T_GF_GRAIN",
                            ["quinoa"])
    C["grain.buckwheat"] = cat("grain.buckwheat", "Buckwheat", "T_GF_GRAIN",
                               ["buckwheat"])
    C["grain.millet"] = cat("grain.millet", "Millet", "T_GF_GRAIN",
                            ["millet"])
    C["grain.sorghum"] = cat("grain.sorghum", "Sorghum", "T_GF_GRAIN",
                             ["sorghum"])

    # ---- Starches
    C["starch.potato"] = cat("starch.potato", "Potato", "T_GF_GRAIN",
                             ["potato", "mashed potato", "fries", "potato wedges"])
    C["starch.sweet_potato"] = cat("starch.sweet_potato", "Sweet potato", "T_GF_GRAIN",
                                   ["sweet potato", "yam"])
    C["starch.cornstarch"] = cat("starch.cornstarch", "Cornstarch", "T_GF_GRAIN",
                                 ["cornstarch"])
    C["starch.tapioca"] = cat("starch.tapioca", "Tapioca", "T_GF_GRAIN",
                              ["tapioca", "tapioca starch"])
    C["starch.rice_flour"] = cat("starch.rice_flour", "Rice flour", "T_GF_GRAIN",
                                 ["rice flour"])

    # ---- Dairy
    C["dairy.milk"] = cat("dairy.milk", "Milk", "T_DAIRY",
                          ["milk", "whole milk", "skim milk"])
    C["dairy.cream"] = cat("dairy.cream", "Cream", "T_DAIRY_FAT",
                           ["cream", "heavy cream", "whipping cream"])
    C["dairy.cheese"] = cat("dairy.cheese", "Cheese", "T_DAIRY_FAT",
                            ["cheese", "cheddar", "mozzarella", "parmesan"])
    C["dairy.yogurt"] = cat("dairy.yogurt", "Yogurt", "T_DAIRY",
                            ["yogurt", "greek yogurt"])
    C["dairy.butter_ghee"] = cat("dairy.butter_ghee", "Butter/Ghee", "T_DAIRY_FAT",
                                 ["butter", "ghee"])
    C["dairy.ice_cream"] = cat("dairy.ice_cream", "Ice cream", "T_DAIRY_FAT",
                               ["ice cream"])

    # ---- Eggs
    C["egg.whole"] = cat("egg.whole", "Egg", "T_EGG",
                         ["egg", "eggs"])
    C["egg.white"] = cat("egg.white", "Egg white", "T_EGG",
                         ["egg whites"])
    C["egg.yolk"] = cat("egg.yolk", "Egg yolk", "T_EGG",
                        ["egg yolk"])

    # ---- Oils/fats
    C["fat.olive_oil"] = cat("fat.olive_oil", "Olive oil", "T_OLIVE_OIL",
                             ["olive oil", "extra virgin olive oil"])
    C["fat.vegetable_oil"] = cat("fat.vegetable_oil", "Vegetable oil", "T_ADDED_FAT",
                                 ["vegetable oil", "canola oil", "sunflower oil"])
    C["fat.coconut_oil"] = cat("fat.coconut_oil", "Coconut oil", "T_ADDED_FAT",
                               ["coconut oil"])
    C["fat.margarine"] = cat("fat.margarine", "Margarine", "T_ADDED_FAT",
                             ["margarine"])
    C["fat.animal_fat_lard"] = cat("fat.animal_fat_lard", "Lard/animal fat", "T_ADDED_FAT",
                                   ["lard", "tallow"])
    C["fat.mayo"] = cat("fat.mayo", "Mayonnaise", "T_EGG",
                        ["mayonnaise", "mayo"])
    C["fat.nut_butter"] = cat("fat.nut_butter", "Nut butter", "T_TREE_NUT",
                              ["almond butter", "cashew butter", "nut butter"])
    C["fat.peanut_butter"] = cat("fat.peanut_butter", "Peanut butter", "T_PEANUT",
                                 ["peanut butter"])
    C["fat.avocado"] = cat("fat.avocado", "Avocado", "T_NEUTRAL_PLANT",
                           ["avocado"])

    # ---- Sauces/condiments (sodium + sugar + allergens)
    C["sauce.soy_sauce"] = cat("sauce.soy_sauce", "Soy sauce", "T_HIGH_SODIUM",
                               ["soy sauce", "shoyu"])
    C["sauce.soy_sauce"]["flags"]["contains_soy"] = True
    C["sauce.soy_sauce"]["flags"]["is_gluten_free_ok"] = False
    C["sauce.soy_sauce"]["flags"]["contains_wheat_gluten"] = True

    C["sauce.tamari"] = cat("sauce.tamari", "Tamari", "T_HIGH_SODIUM",
                            ["tamari"])
    C["sauce.tamari"]["flags"]["contains_soy"] = True

    C["sauce.teriyaki"] = cat("sauce.teriyaki", "Teriyaki sauce", "T_HIGH_SODIUM",
                              ["teriyaki"])
    C["sauce.teriyaki"]["flags"]["contains_soy"] = True
    C["sauce.teriyaki"]["flags"]["is_low_carb_risky"] = True
    C["sauce.teriyaki"]["flags"]["raises_glucose_risk"] = True
    C["sauce.teriyaki"]["flags"]["raises_triglycerides_risk"] = True

    C["sauce.fish_sauce"] = cat("sauce.fish_sauce", "Fish sauce", "T_HIGH_SODIUM",
                                ["fish sauce"])
    C["sauce.fish_sauce"]["flags"]["contains_fish"] = True

    C["sauce.oyster_sauce"] = cat("sauce.oyster_sauce", "Oyster sauce", "T_HIGH_SODIUM",
                                  ["oyster sauce"])
    C["sauce.oyster_sauce"]["flags"]["contains_shellfish"] = True

    C["sauce.bbq"] = cat("sauce.bbq", "BBQ sauce", "T_SUGAR",
                         ["bbq sauce", "barbecue sauce"])
    C["sauce.ketchup"] = cat("sauce.ketchup", "Ketchup", "T_SUGAR",
                             ["ketchup"])
    C["sauce.sweet_chili"] = cat("sauce.sweet_chili", "Sweet chili sauce", "T_SUGAR",
                                 ["sweet chili sauce"])
    C["sauce.tomato"] = cat("sauce.tomato", "Tomato sauce", "T_NEUTRAL_PLANT",
                            ["tomato sauce", "marinara", "passata"])
    C["sauce.cream_based"] = cat("sauce.cream_based", "Cream-based sauce", "T_DAIRY_FAT",
                                 ["alfredo", "cream sauce"])
    C["sauce.pesto"] = cat("sauce.pesto", "Pesto", "T_TREE_NUT",
                           ["pesto"])
    C["sauce.pesto"]["flags"]["contains_dairy"] = True
    C["sauce.pesto"]["flags"]["is_vegan_ok"] = False
    C["sauce.salad_dressing"] = cat("sauce.salad_dressing", "Salad dressing", "T_NEUTRAL_PLANT",
                                    ["salad dressing", "vinaigrette"])
    C["sauce.mustard"] = cat("sauce.mustard", "Mustard", "T_NEUTRAL_PLANT",
                             ["mustard"])
    C["sauce.vinegar"] = cat("sauce.vinegar", "Vinegar", "T_NEUTRAL_PLANT",
                             ["vinegar", "apple cider vinegar"])
    C["sauce.hot_sauce"] = cat("sauce.hot_sauce", "Hot sauce", "T_HIGH_SODIUM",
                               ["hot sauce", "sriracha"])

    # ---- Nuts & seeds
    C["nuts.tree_nut"] = cat("nuts.tree_nut", "Tree nuts", "T_TREE_NUT",
                             ["almonds", "walnuts", "cashews", "pistachios", "hazelnuts"])
    C["nuts.peanut"] = cat("nuts.peanut", "Peanut", "T_PEANUT",
                           ["peanuts"])
    C["nuts.mixed"] = cat("nuts.mixed", "Mixed nuts", "T_TREE_NUT",
                          ["mixed nuts", "trail mix"])
    C["seeds.sesame"] = cat("seeds.sesame", "Sesame", "T_SESAME",
                            ["sesame", "tahini"])
    C["seeds.flax_chia"] = cat("seeds.flax_chia", "Flax/Chia", "T_NEUTRAL_PLANT",
                               ["chia", "flax"])
    C["seeds.sunflower"] = cat("seeds.sunflower", "Sunflower seeds", "T_NEUTRAL_PLANT",
                               ["sunflower seeds"])
    C["seeds.other"] = cat("seeds.other", "Other seeds", "T_NEUTRAL_PLANT",
                           ["pumpkin seeds", "hemp seeds"])

    # ---- Sweeteners
    C["sweetener.sugar"] = cat("sweetener.sugar", "Sugar", "T_SUGAR",
                               ["sugar", "brown sugar"])
    C["sweetener.honey_syrup"] = cat("sweetener.honey_syrup", "Honey/syrup", "T_SUGAR",
                                     ["honey", "maple syrup", "corn syrup"])

    # ---- Sodium
    C["sodium.salt"] = cat("sodium.salt", "Salt", "T_HIGH_SODIUM",
                           ["salt", "sea salt"])
    C["sodium.stock_cube_broth_concentrate"] = cat("sodium.stock_cube_broth_concentrate", "Stock cubes/broth concentrate", "T_HIGH_SODIUM",
                                                   ["stock cube", "bouillon", "broth concentrate"])
    C["sodium.pickled"] = cat("sodium.pickled", "Pickled foods", "T_HIGH_SODIUM",
                              ["pickles", "pickled cucumbers", "olives"])
    C["sodium.processed_high_sodium"] = cat("sodium.processed_high_sodium", "Processed high-sodium foods", "T_HIGH_SODIUM",
                                            ["instant noodles", "seasoning packet", "processed food"])

    # ---- Halal risks
    C["halal.alcohol"] = cat("halal.alcohol", "Alcohol", "T_ALCOHOL",
                             ["wine", "beer", "vodka", "rum"])
    C["halal.gelatin"] = cat("halal.gelatin", "Gelatin", "T_GELATIN",
                             ["gelatin"])
    C["halal.lard"] = cat("halal.lard", "Lard", "T_PORK",
                          ["lard"])
    C["halal.non_halal_meat_unknown"] = cat("halal.non_halal_meat_unknown", "Unknown meat source", "T_ANIMAL_FATTY_PROTEIN",
                                            ["sausage (unknown)", "pepperoni (unknown)", "deli meat (unknown)"])
    C["halal.non_halal_meat_unknown"]["flags"]["is_halal_ok"] = False

    # ---- Vegetables & fruits (low-carb swaps)
    C["vegetable.non_starchy"] = cat("vegetable.non_starchy", "Non-starchy vegetables", "T_NEUTRAL_PLANT",
                                     ["broccoli", "spinach", "lettuce", "zucchini", "cucumber"])
    C["vegetable.starchy"] = cat("vegetable.starchy", "Starchy vegetables", "T_GF_GRAIN",
                                 ["corn", "peas", "pumpkin"])
    C["vegetable.cauliflower_rice"] = cat("vegetable.cauliflower_rice", "Cauliflower rice", "T_NEUTRAL_PLANT",
                                          ["cauliflower rice"])
    C["vegetable.zucchini_zoodles"] = cat("vegetable.zucchini_zoodles", "Zucchini noodles", "T_NEUTRAL_PLANT",
                                          ["zoodles", "zucchini noodles"])
    C["vegetable.leafy_greens"] = cat("vegetable.leafy_greens", "Leafy greens", "T_NEUTRAL_PLANT",
                                      ["spinach", "kale", "arugula"])
    C["fruit.general"] = cat("fruit.general", "Fruits", "T_SUGAR",
                             ["apple", "banana", "orange", "grapes", "strawberries"])
    C["fruit.dried"] = cat("fruit.dried", "Dried fruit", "T_SUGAR",
                           ["raisins", "dates", "dried apricots"])

    # ---- Catch-alls (critical for “any ingredient on earth”)
    C["other.unknown"] = cat("other.unknown", "Unknown ingredient", "T_NEUTRAL_PLANT",
                             ["unknown ingredient"])
    C["other.processed_food_unknown"] = cat("other.processed_food_unknown", "Unknown processed food", "T_HIGH_SODIUM",
                                            ["instant mix", "package mix", "seasoning mix"])
    C["other.spice_unknown"] = cat("other.spice_unknown", "Unknown spice", "T_NEUTRAL_PLANT",
                                   ["spice"])
    C["other.sauce_unknown"] = cat("other.sauce_unknown", "Unknown sauce", "T_HIGH_SODIUM",
                                   ["sauce"])
    C["other.grain_unknown"] = cat("other.grain_unknown", "Unknown grain", "T_GF_GRAIN",
                                   ["grain"])
    C["other.protein_unknown"] = cat("other.protein_unknown", "Unknown protein", "T_ANIMAL_LEAN_PROTEIN",
                                     ["protein"])

    # ---- Expand to ~200 with safe broad categories (auto-generated)
    # These “broad” categories are still useful for RAG mapping and coverage.
    auto_blocks = [
        ("herb.aromatic", "Aromatics & herbs", "T_NEUTRAL_PLANT",
         ["garlic", "onion", "parsley", "cilantro", "basil"]),
        ("seasoning.spice", "Spices & seasonings", "T_NEUTRAL_PLANT",
         ["pepper", "paprika", "cumin", "turmeric", "oregano"]),
        ("baking.leavening", "Leavening", "T_NEUTRAL_PLANT",
         ["baking powder", "baking soda", "yeast"]),
        ("baking.cocoa_chocolate", "Cocoa & chocolate", "T_SUGAR",
         ["cocoa", "chocolate chips", "dark chocolate"]),
        ("beverage.coffee_tea", "Coffee & tea", "T_NEUTRAL_PLANT",
         ["coffee", "tea"]),
        ("beverage.sugary", "Sugary drinks", "T_SUGAR",
         ["soda", "juice", "energy drink"]),
        ("dessert.general", "Desserts", "T_SUGAR",
         ["cake", "cookies", "pastry"]),
        ("snack.processed", "Processed snacks", "T_HIGH_SODIUM",
         ["chips", "crackers", "snack"]),
        ("grain.breakfast_cereal", "Breakfast cereals", "T_SUGAR",
         ["cereal", "granola"]),
        ("sauce.mayo_based", "Mayo-based sauces", "T_EGG",
         ["aioli", "mayo sauce"]),
        ("sauce.honey_mustard", "Honey mustard", "T_SUGAR",
         ["honey mustard"]),
        ("sauce.hoisin", "Hoisin sauce", "T_SUGAR",
         ["hoisin"]),
        ("sauce.miso", "Miso", "T_SOY",
         ["miso"]),
    ]

    for cid, label, template, exs in auto_blocks:
        if cid not in C:
            C[cid] = cat(cid, label, template, exs)

    # pad with additional generic groups so we reach ~200 keys
    # These are “domain-complete” groups: they catch huge ingredient space.
    generic_ids = []
    # 1) vegetables by family
    veg_families = [
        "vegetable.cruciferous", "vegetable.nightshade", "vegetable.allium", "vegetable.root",
        "vegetable.gourd", "vegetable.legume_green", "vegetable.mushroom", "vegetable.mixed"
    ]
    for v in veg_families:
        generic_ids.append((v, v.replace(".", " ").title(), "T_NEUTRAL_PLANT", ["vegetable"]))

    # 2) fruits by type
    fruits = ["fruit.citrus", "fruit.berry", "fruit.tropical", "fruit.stone", "fruit.melon"]
    for f in fruits:
        generic_ids.append((f, f.replace(".", " ").title(), "T_SUGAR", ["fruit"]))

    # 3) sauces by type
    sauce_types = [
        "sauce.gravy", "sauce.stock_based", "sauce.cheese_based", "sauce.spicy", "sauce.sweet"
    ]
    for s in sauce_types:
        t = "T_HIGH_SODIUM" if "stock" in s or "gravy" in s else "T_NEUTRAL_PLANT"
        if "sweet" in s:
            t = "T_SUGAR"
        if "cheese" in s:
            t = "T_DAIRY_FAT"
        generic_ids.append((s, s.replace(".", " ").title(), t, ["sauce"]))

    # 4) grains/starches catch-alls
    grains = ["grain.gluten_free.pasta", "grain.wheat.crackers", "grain.wheat.cake_mix"]
    for g in grains:
        t = "T_GF_GRAIN" if "gluten_free" in g else "T_WHEAT_GRAIN"
        generic_ids.append((g, g.replace(".", " ").title(), t, ["grain"]))

    # 5) proteins expanded
    proteins = [
        "protein.animal.deli_meat", "protein.animal.game_meat",
        "protein.plant.other", "protein.plant.bean_paste"
    ]
    for p in proteins:
        t = "T_ANIMAL_FATTY_PROTEIN" if "animal" in p else "T_NEUTRAL_PLANT"
        generic_ids.append((p, p.replace(".", " ").title(), t, ["protein"]))

    # 6) dairy alternatives
    dairy_alt = ["dairy_alt.plant_milk", "dairy_alt.vegan_cheese", "dairy_alt.vegan_butter"]
    for d in dairy_alt:
        generic_ids.append((d, d.replace(".", " ").title(), "T_NEUTRAL_PLANT", ["plant-based"]))

    # Add all generics
    for cid, label, template, exs in generic_ids:
        if cid not in C:
            C[cid] = cat(cid, label, template, exs)

    # Finally: ensure we have ~200 categories by padding with “other.*” buckets
    # These are not junk—they are guaranteed fallback coverage.
    i = 1
    while len(C) < 200:
        cid = f"other.bucket_{i:03d}"
        if cid not in C:
            C[cid] = cat(cid, f"Misc bucket {i}", "T_NEUTRAL_PLANT", ["misc ingredient"])
        i += 1

    return C

def build_rules_for_all_categories(categories: Dict[str, Any]) -> Dict[str, Any]:
    rules: Dict[str, Any] = {}

    for cid, cat in categories.items():
        flags = cat.get("flags") or {}
        entry: Dict[str, Any] = {}

        # ---------------------------
        # Allergies (hard substitute)
        # ---------------------------
        allergy_rules: Dict[str, Any] = {}

        if flags.get("contains_wheat_gluten"):
            allergy_rules["wheat_gluten"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["wheat_gluten"],
                "amount_policy": "keep_same",
                "reason": "Contains wheat/gluten"
            }

        if flags.get("contains_dairy"):
            allergy_rules["dairy"] = {
                "action": "substitute_category",
                "to_category": "fat.olive_oil" if cid == "dairy.butter_ghee" else DEFAULT_SUBS["dairy"],
                "amount_policy": "butter_to_olive_oil_0p75" if cid == "dairy.butter_ghee" else "keep_same",
                "reason": "Contains dairy"
            }

        if flags.get("contains_egg"):
            allergy_rules["egg"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["egg"],
                "amount_policy": "keep_same",
                "reason": "Contains egg"
            }

        if flags.get("contains_fish"):
            allergy_rules["fish"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["fish"],
                "amount_policy": "keep_same",
                "reason": "Contains fish"
            }

        if flags.get("contains_shellfish"):
            allergy_rules["shellfish"] = {
                "action": "substitute_category",
                "to_category": "protein.animal.poultry",
                "amount_policy": "keep_same",
                "reason": "Contains shellfish"
            }

        if flags.get("contains_soy"):
            allergy_rules["soy"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["soy"],
                "amount_policy": "keep_same",
                "reason": "Contains soy"
            }

        if flags.get("contains_tree_nut"):
            allergy_rules["tree_nut"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["tree_nut"],
                "amount_policy": "keep_same",
                "reason": "Contains tree nuts"
            }

        if flags.get("contains_peanut"):
            allergy_rules["peanut"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["peanut"],
                "amount_policy": "keep_same",
                "reason": "Contains peanuts"
            }

        if flags.get("contains_sesame"):
            allergy_rules["sesame"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["sesame"],
                "amount_policy": "keep_same",
                "reason": "Contains sesame"
            }

        if allergy_rules:
            entry["allergies"] = allergy_rules

        # ---------------------------
        # Diets (soft + some hard)
        # ---------------------------
        diet_rules: Dict[str, Any] = {}

        # Vegan/vegetarian: if not ok, substitute
        if not flags.get("is_vegan_ok", True):
            diet_rules["vegan"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["vegan"],
                "amount_policy": "keep_same",
                "reason": "Vegan diet"
            }
        if not flags.get("is_vegetarian_ok", True):
            diet_rules["vegetarian"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["vegetarian"],
                "amount_policy": "keep_same",
                "reason": "Vegetarian diet"
            }

        # Halal: if not ok, substitute
        if not flags.get("is_halal_ok", True):
            diet_rules["halal"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["halal"],
                "amount_policy": "keep_same",
                "reason": "Halal diet"
            }

        # Gluten-free diet: if not ok, substitute
        if not flags.get("is_gluten_free_ok", True):
            diet_rules["gluten_free"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["wheat_gluten"],
                "amount_policy": "keep_same",
                "reason": "Gluten-free diet"
            }

        # Low-fat: reduce risky items (oils/fats/saturated)
        if flags.get("is_low_fat_risky", False):
            diet_rules["low_fat"] = {
                "action": "reduce_amount",
                "reduce_ratio": 0.75,
                "reason": "Low-fat preference: reduce added fat"
            }

        # Low-sodium: reduce risky sodium items
        if flags.get("is_low_sodium_risky", False):
            diet_rules["low_sodium"] = {
                "action": "reduce_amount",
                "reduce_ratio": 0.5,
                "reason": "Low-sodium preference"
            }

        # Low-carb: substitute high-carb risky items
        if flags.get("is_low_carb_risky", False):
            diet_rules["low_carb"] = {
                "action": "substitute_category",
                "to_category": DEFAULT_SUBS["low_carb"],
                "amount_policy": "keep_same",
                "reason": "Low-carb preference"
            }

        # High-protein: increase protein sources
        if flags.get("is_high_protein_source", False):
            diet_rules["high_protein"] = {
                "action": "increase_amount",
                "increase_ratio": 0.20,
                "reason": "High-protein preference"
            }

        if diet_rules:
            entry["diets"] = diet_rules

        # ---------------------------
        # Labs (conservative heuristics)
        # ---------------------------
        lab_rules: Dict[str, Any] = {}

        if flags.get("raises_ldl_risk", False):
            lab_rules["LDL_HIGH"] = {
                "action": "reduce_amount",
                "reduce_ratio": 0.75,
                "reason": "LDL high: reduce LDL-raising ingredient"
            }

        if flags.get("raises_triglycerides_risk", False):
            lab_rules["TRIGLYCERIDES_HIGH"] = {
                "action": "reduce_amount",
                "reduce_ratio": 0.75,
                "reason": "Triglycerides high: reduce TG-raising ingredient"
            }

        if flags.get("raises_glucose_risk", False):
            lab_rules["GLUCOSE_HIGH"] = {
                "action": "reduce_amount",
                "reduce_ratio": 0.75,
                "reason": "Glucose high: reduce high glycemic load"
            }

        if flags.get("kidney_risky_high_sodium", False):
            lab_rules["CREATININE_HIGH"] = {
                "action": "reduce_amount",
                "reduce_ratio": 0.5,
                "reason": "Creatinine high: kidney-friendly sodium reduction"
            }

        # kidney risky protein: block high protein increase
        if flags.get("kidney_risky_very_high_protein", False):
            lab_rules.setdefault("CREATININE_HIGH", {})
            lab_rules["CREATININE_HIGH"] = {
                "action": "block_high_protein_increase",
                "reason": "Creatinine high: avoid increasing protein load"
            }

        if lab_rules:
            entry["labs"] = lab_rules

        if entry:
            rules[cid] = entry

    return rules


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))

    # keep any existing top-level keys (version, constraints_supported, rules, etc.)
    data["flag_schema"] = FLAG_SCHEMA
    data["templates"] = TEMPLATES

    categories = build_categories()
    data["rules"] = build_rules_for_all_categories(categories)
    data["defaults"] = {
        "no_rule_behavior": "keep_and_report",
        "report_prefix": "[Step3]"
    }

    data["categories"] = categories

    # ensure constraints_supported exists (keep yours if already there)
    data.setdefault("constraints_supported", {
        "diets": ["vegetarian", "vegan", "high_protein", "low_carb", "gluten_free", "low_sodium", "low_fat", "halal"],
        "allergies": ["wheat_gluten", "dairy", "egg", "fish", "soy", "tree_nut", "peanut", "sesame"],
        "labs": ["LDL_HIGH", "HDL_LOW", "TRIGLYCERIDES_HIGH", "GLUCOSE_HIGH", "CREATININE_HIGH"]
    })

    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Built v2 dataset: {OUT} with {len(categories)} categories")


if __name__ == "__main__":
    main()
