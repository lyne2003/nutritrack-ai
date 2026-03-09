from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.services.substitution.loader import load_rules_v3
from app.services.substitution.llm_verifier import (
    ALL_FLAGS,
    classify_and_flag_with_llm,
    suggest_fallback_action_with_llm,
)


# -------------------------
# Helpers
# -------------------------
def _normalize_constraints(
    diets: Optional[List[str]],
    allergies: Optional[List[str]],
    lab_flags: Optional[List[str]],
) -> Dict[str, Any]:
    return {
        "diets": [d.strip().lower() for d in (diets or [])],
        "allergies": [a.strip().lower() for a in (allergies or [])],
        "lab_flags": [l.strip().upper() for l in (lab_flags or [])],
    }


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        s = str(x).strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None


def _format_final_line(item: Dict[str, Any]) -> str:
    amt = item.get("scaled_number_of_units")
    unit = (item.get("measurement_description") or "").strip()
    name = (item.get("food_name") or "").strip()

    if amt is None or str(amt).strip() == "":
        return name
    if unit:
        return f"{amt} {unit} {name}".replace("  ", " ").strip()
    return f"{amt} {name}".replace("  ", " ").strip()


def _ensure_all_flags(flags: Dict[str, Any]) -> Dict[str, bool]:
    """
    Ensure every key in ALL_FLAGS exists and is boolean.
    Also ensure 'violates_halal' exists because engine expects it.
    """
    out = {k: bool(flags.get(k, False)) for k in ALL_FLAGS}
    if "violates_halal" not in out:
        out["violates_halal"] = bool(flags.get("violates_halal", False))
    return out


def _constraint_priority(rules: Dict[str, Any]) -> List[str]:
    """
    Locked priority (as per spec):
      allergies -> halal -> diet_bans -> labs -> diet_prefs
    """
    return ["allergies", "halal", "diet_bans", "labs", "diet_prefs"]


def _build_all_category_candidates(rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    cats = rules.get("categories") or {}
    out: List[Dict[str, Any]] = []
    for cid, c in cats.items():
        out.append({"category_id": cid, "label": c.get("label"), "examples": c.get("examples") or []})
    return out


# -------------------------
# Deterministic flags from category (post-substitution truth)
# -------------------------
def _flags_from_category(category_id: str) -> Dict[str, bool]:
    """
    Deterministic baseline flags derived from our general category.
    Used AFTER substitutions so flags match the new ingredient/category.
    """
    cid = (category_id or "").strip()

    base: Dict[str, bool] = {k: False for k in ALL_FLAGS}
    if "violates_halal" not in base:
        base["violates_halal"] = False

    # Plant-based dairy alternatives MUST NOT be dairy
    is_dairy_alt = cid.startswith("dairy_alt_")

    # ---- Allergen presence ----
    if cid.startswith("dairy_") and not is_dairy_alt:
        base["contains_dairy"] = True
    if cid == "protein_eggs":
        base["contains_egg"] = True
    if cid == "protein_fish_seafood":
        base["contains_fish"] = True
    if cid == "protein_soy":
        base["contains_soy"] = True
    if cid == "protein_nuts_tree":
        base["contains_tree_nut"] = True
    if cid == "protein_peanut":
        base["contains_peanut"] = True
    if cid == "protein_seeds_sesame":
        base["contains_sesame"] = True
    if cid.startswith("grain_wheat_") or cid == "grain_other_gluten":
        base["contains_wheat_gluten"] = True

    # ---- Vegan / Vegetarian friendliness ----
    animal_meat = {
        "protein_poultry",
        "protein_red_meat",
        "protein_processed_meat",
        "protein_fish_seafood",
        "protein_organs",
    }

    if is_dairy_alt:
        # plant alternatives are vegan-friendly
        base["is_vegan_friendly"] = True
        base["is_vegetarian_friendly"] = True
        base["contains_dairy"] = False
    elif cid in animal_meat:
        base["is_vegan_friendly"] = False
        base["is_vegetarian_friendly"] = False
    elif cid == "protein_eggs" or cid.startswith("dairy_"):
        base["is_vegan_friendly"] = False
        base["is_vegetarian_friendly"] = True
    else:
        base["is_vegan_friendly"] = True
        base["is_vegetarian_friendly"] = True

    # ---- Gluten-free friendliness ----
    base["is_gluten_free_friendly"] = not base.get("contains_wheat_gluten", False)

    # ---- Soft diet risk flags ----
    if cid.startswith("grain_wheat_") or cid in (
        "grain_rice",
        "grain_corn",
        "grain_oats",
        "grain_other_gluten",
        "starch_potato",
        "starch_starchy_veg",
    ):
        base["is_low_carb_risky"] = True

    if cid in ("dairy_butter_ghee", "dairy_milk_cream", "dairy_cheese", "fat_oils", "protein_processed_meat"):
        base["is_low_fat_risky"] = True

    if cid in ("sodium_salt_and_broth", "sauce_condiment_high_sodium", "protein_processed_meat"):
        base["is_low_sodium_risky"] = True
        base["kidney_risky_high_sodium"] = True

    # mark very-high-protein kidney risk only for the worst offenders
    if cid in ("protein_red_meat", "protein_processed_meat", "protein_organs"):
        base["kidney_risky_very_high_protein"] = True

    # protein source (broad)
    if cid.startswith("protein_"):
        base["is_high_protein_source"] = True

    # ---- Labs triggers ----
    if cid in ("dairy_butter_ghee", "dairy_milk_cream", "dairy_cheese", "protein_processed_meat", "protein_red_meat", "protein_organs"):
        base["raises_ldl_risk"] = True

    if cid.startswith("grain_wheat_") or cid in ("grain_rice", "starch_potato", "sugar_sweeteners", "grain_other_gluten"):
        base["raises_glucose_risk"] = True
        base["raises_triglycerides_risk"] = True

    # ---- Meta ----
    if cid in ("protein_processed_meat", "sauce_condiment_high_sodium", "sodium_salt_and_broth"):
        base["is_processed"] = True

    if cid.startswith("grain_wheat_") or cid == "grain_other_gluten":
        base["is_refined_carb"] = True

    return base


# -------------------------
# Trigger mapping
# -------------------------
def _is_triggered(block: str, key: str, flags: Dict[str, bool]) -> bool:
    # Allergies
    if block == "allergies":
        mapping = {
            "wheat_gluten": "contains_wheat_gluten",
            "dairy": "contains_dairy",
            "egg": "contains_egg",
            "fish": "contains_fish",
            "soy": "contains_soy",
            "tree_nut": "contains_tree_nut",
            "peanut": "contains_peanut",
            "sesame": "contains_sesame",
        }
        f = mapping.get(key)
        return bool(flags.get(f, False)) if f else False

    # Halal
    if block == "halal" and key == "halal":
        return bool(flags.get("violates_halal", False))

    # Labs
    if block == "labs":
        if key == "LDL_HIGH":
            return bool(flags.get("raises_ldl_risk", False))
        if key == "TRIGLYCERIDES_HIGH":
            return bool(flags.get("raises_triglycerides_risk", False))
        if key == "GLUCOSE_HIGH":
            return bool(flags.get("raises_glucose_risk", False))

        # ✅ Fix: CREATININE_HIGH triggers ONLY for kidney-relevant risk flags
        if key == "CREATININE_HIGH":
            return bool(flags.get("kidney_risky_high_sodium", False) or flags.get("kidney_risky_very_high_protein", False))

        # ✅ Fix: HDL_LOW should not trigger everywhere; mostly relevant to fish/healthy fats
        if key == "HDL_LOW":
            return bool(flags.get("contains_fish", False))

        return False

    # Diet bans (hard exclusions)
    if block == "diet_bans":
        if key == "vegan":
            return not bool(flags.get("is_vegan_friendly", False))
        if key == "vegetarian":
            return not bool(flags.get("is_vegetarian_friendly", False))
        if key == "gluten_free":
            return (not bool(flags.get("is_gluten_free_friendly", False))) or bool(flags.get("contains_wheat_gluten", False))
        return False

    # Diet preferences (soft)
    if block == "diet_prefs":
        if key == "low_carb":
            return bool(flags.get("is_low_carb_risky", False))
        if key == "low_fat":
            return bool(flags.get("is_low_fat_risky", False))
        if key == "low_sodium":
            return bool(flags.get("is_low_sodium_risky", False)) or bool(flags.get("kidney_risky_high_sodium", False))
        if key == "high_protein":
            # Trigger ONLY if this ingredient is NOT already a protein source.
            # (Otherwise it would block other diet prefs like low_fat/low_sodium.)
            return not bool(flags.get("is_high_protein_source", False))
        return False

    return False


# -------------------------
# Rule engine
# -------------------------
def _apply_amount_multiplier(item: Dict[str, Any], mult: float) -> bool:
    x = _safe_float(item.get("scaled_number_of_units"))
    if x is None:
        return False
    item["scaled_number_of_units"] = f"{(x * float(mult)):.3g}"
    return True


def _get_category_rule(
    rules: Dict[str, Any],
    category_id: str,
    block: str,
    key: str,
) -> Optional[Dict[str, Any]]:
    cat_rules = (rules.get("category_rules") or {}).get(category_id) or {}

    if block == "diet_bans":
        return (cat_rules.get("diets") or {}).get(key)

    if block == "diet_prefs":
        soft = (cat_rules.get("diets_soft") or {}).get(key)
        if soft:
            return soft
        return (cat_rules.get("diets") or {}).get(key)

    return (cat_rules.get(block) or {}).get(key)


def _infer_category_for_text(
    *,
    rules: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    text: str,
    model: str,
) -> str:
    """
    Used only when LLM fallback suggests a substitute but doesn't provide a category.
    We'll classify the substitute text to get a best-effort final_category_id.
    """
    text = (text or "").strip()
    if not text:
        return "other_unknown"

    llm_out = classify_and_flag_with_llm(
        ingredient_line=text,
        candidates=candidates,
        model=model,
    )
    return llm_out.get("category_id") or "other_unknown"


def _apply_rule_action(
    *,
    rules: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    item: Dict[str, Any],
    original_line: str,
    prefix: str,
    block: str,
    key: str,
    rule: Dict[str, Any],
    constraints: Dict[str, Any],
    flags: Dict[str, bool],
    model: str,
    state: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str], bool]:
    """
    Returns: (new_item, report_lines, stop_processing_for_this_ingredient)
    stop=True means we applied a decisive action and stop further blocks.
    """
    out = dict(item)
    rep: List[str] = []

    action = (rule.get("action") or "").strip().lower()
    reason_user = rule.get("reason_user") or "it conflicts with your constraints"

    if action == "substitute":
        # base substitute from the rule
        sub_name = rule.get("substitute_name") or "safe alternative"
        to_cat = rule.get("to_category") or out.get("final_category_id") or "other_unknown"

        # ✅ Fix 2: conditional_substitutes support
        conditional = rule.get("conditional_substitutes") or {}
        user_allergies = set((constraints.get("allergies") or []))

        for allergy_key, alt in conditional.items():
            if allergy_key in user_allergies:
                alt = alt or {}
                if alt.get("substitute_name"):
                    sub_name = alt["substitute_name"]
                if alt.get("to_category"):
                    to_cat = alt["to_category"]
                break

        out["final_category_id"] = to_cat
        out["food_name"] = sub_name

        # ✅ Fix: store pre-change flags, then refresh deterministically for the NEW category
        out["original_flags"] = dict(out.get("flags") or {})
        out["flags"] = _flags_from_category(to_cat)

        # amount policy
        amount_policy = rule.get("amount_policy") or {"type": "keep_same"}
        if amount_policy.get("type") == "multiplier":
            mult = float(amount_policy.get("value", 1.0))
            ok = _apply_amount_multiplier(out, mult)
            if not ok:
                rep.append(f"{prefix} {block}({key}): Wanted to adjust amount but amount is non-numeric.")

        rep.append(f"{prefix} {block}({key}): Replaced '{original_line}' with '{sub_name}' because {reason_user}.")

        if block == "allergies" and constraints.get("diets") and not state.get("priority_note_added", False):
            rep.append(
                f"{prefix} Note: Allergies are prioritized over halal/labs/diets. Diet preferences were applied only if they didn’t conflict."
            )
            state["priority_note_added"] = True

        return out, rep, True

    if action == "reduce_amount":
        out["original_flags"] = dict(out.get("flags") or {})
        ratio = float(rule.get("reduce_ratio") or 0.75)
        ok = _apply_amount_multiplier(out, ratio)
        if ok:
            rep.append(f"{prefix} {block}({key}): Reduced amount of '{original_line}' because {reason_user}.")
        else:
            rep.append(f"{prefix} {block}({key}): Wanted to reduce amount but amount is non-numeric.")
        return out, rep, True

    if action == "increase_amount":
        if "CREATININE_HIGH" in (constraints.get("lab_flags") or []) or flags.get("kidney_risky_very_high_protein", False):
            rep.append(
                f"{prefix} diets(high_protein): You requested high protein, but we avoided increasing protein due to kidney-safe conservative rule."
            )
            return out, rep, True
        out["original_flags"] = dict(out.get("flags") or {})


        ratio = 1.0 + float(rule.get("increase_ratio") or 0.20)
        ok = _apply_amount_multiplier(out, ratio)
        if ok:
            rep.append(f"{prefix} {block}({key}): Increased amount of '{original_line}' because {reason_user}.")
        else:
            rep.append(f"{prefix} {block}({key}): Wanted to increase amount but amount is non-numeric.")
        return out, rep, True

    if action == "keep":
        out["original_flags"] = dict(out.get("flags") or {})
        rep.append(f"{prefix} {block}({key}): No change needed ({reason_user}).")
        return out, rep, True

    if action == "llm_fallback":
        rep.append(f"{prefix} {block}({key}): No predefined rule; AI fallback will be used.")
        return out, rep, True

    rep.append(f"{prefix} {block}({key}): No change (unknown action).")
    return out, rep, True


def _apply_constraints_for_item(
    *,
    rules: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    item: Dict[str, Any],
    flags: Dict[str, bool],
    constraints: Dict[str, Any],
    prefix: str,
    model: str,
    state: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    out = dict(item)
    report: List[str] = []

    original_line = item.get("ingredient_description") or item.get("food_name") or "ingredient"
    category_id = out.get("mapped_category_id") or "other_unknown"
    priority = _constraint_priority(rules)

    diets = set(constraints.get("diets") or [])
    allergies = set(constraints.get("allergies") or [])
    labs = set(constraints.get("lab_flags") or [])

    triggered_tags: List[str] = []

    def add_trigger(block: str, key: str):
        triggered_tags.append(f"{block}:{key}")

    for block in priority:
        if block == "allergies":
            keys = sorted(list(allergies))
        elif block == "halal":
            keys = ["halal"] if ("halal" in diets) else []
        elif block == "diet_bans":
            keys = [k for k in ["vegan", "vegetarian", "gluten_free"] if k in diets]
        elif block == "labs":
            keys = sorted(list(labs))
        elif block == "diet_prefs":
            banned = {"vegan", "vegetarian", "gluten_free", "halal"}
            keys = sorted([k for k in diets if k not in banned])
        else:
            keys = []

        for key in keys:
            if not _is_triggered(block, key, flags):
                continue

            add_trigger(block, key)

            rule = _get_category_rule(rules, category_id, block, key)

            if rule:
                out, rep, stop = _apply_rule_action(
                    rules=rules,
                    candidates=candidates,
                    item=out,
                    original_line=original_line,
                    prefix=prefix,
                    block=block,
                    key=key,
                    rule=rule,
                    constraints=constraints,
                    flags=flags,
                    model=model,
                    state=state,
                )
                report.extend(rep)
                if stop:
                    return out, report

            # No rule exists but triggered → LLM fallback allowed
            defaults = rules.get("defaults") or {}
            if defaults.get("llm_fallback_allowed", True):
                fb = suggest_fallback_action_with_llm(
                    ingredient_line=original_line,
                    canonical_name=out.get("food_name") or original_line,
                    category_id=category_id,
                    triggered=triggered_tags,
                    constraints=constraints,
                    priority=priority,
                    model=model,
                )

                action = (fb.get("action") or "").strip().lower()
                reason_user = fb.get("reason_user") or "it conflicts with your constraints"

                if action == "substitute" and fb.get("substitute_name"):
                    sub_name = str(fb["substitute_name"]).strip()

                    # ✅ Fix: determine a NEW final category for fallback substitutions
                    new_cat = fb.get("to_category")
                    if not new_cat:
                        new_cat = _infer_category_for_text(rules=rules, candidates=candidates, text=sub_name, model=model)

                    out["food_name"] = sub_name
                    out["final_category_id"] = new_cat

                    out["original_flags"] = dict(out.get("flags") or {})
                    out["flags"] = _flags_from_category(new_cat)

                    mult = fb.get("amount_multiplier")
                    if isinstance(mult, (int, float)):
                        _apply_amount_multiplier(out, float(mult))

                    report.append(
                        f"{prefix} {block}({key}): No predefined rule for category '{category_id}'. AI suggested replacing '{original_line}' with '{sub_name}' because {reason_user}."
                    )
                    if block == "allergies" and constraints.get("diets") and not state.get("priority_note_added",
                                                                                           False):
                        report.append(
                            f"{prefix} Note: Allergies are prioritized over halal/labs/diets. Diet preferences were applied only if they didn’t conflict."
                        )
                        state["priority_note_added"] = True

                    return out, report

                if action == "reduce_amount":
                    mult = fb.get("amount_multiplier")
                    if isinstance(mult, (int, float)):
                        ok = _apply_amount_multiplier(out, float(mult))
                        if ok:
                            report.append(
                                f"{prefix} {block}({key}): No predefined rule for category '{category_id}'. AI reduced amount of '{original_line}' because {reason_user}."
                            )
                        else:
                            report.append(f"{prefix} {block}({key}): AI wanted to reduce amount but amount is non-numeric.")
                    else:
                        _apply_amount_multiplier(out, 0.75)
                        report.append(
                            f"{prefix} {block}({key}): No predefined rule for category '{category_id}'. AI reduced amount of '{original_line}' because {reason_user}."
                        )
                    return out, report

                report.append(
                    f"{prefix} {block}({key}): No predefined rule for category '{category_id}'. AI kept '{original_line}' because it could not propose a safe change."
                )
                return out, report

    report.append(f"{prefix} No change: '{original_line}' did not conflict with your constraints.")
    return out, report


# -------------------------
# Main Step 3 entrypoint
# -------------------------
def run_step3_substitution(

    scaled_struct: List[Dict[str, Any]],
    diets: Optional[List[str]] = None,
    allergies: Optional[List[str]] = None,
    lab_flags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    rules = load_rules_v3()
    constraints = _normalize_constraints(diets, allergies, lab_flags)

    defaults = rules.get("defaults", {}) or {}
    prefix = defaults.get("report_prefix", "[Step3]")
    model = str(defaults.get("llm_fallback_model") or "gpt-4.1-mini")

    candidates = _build_all_category_candidates(rules)

    state = {"priority_note_added": False}

    final_struct: List[Dict[str, Any]] = []
    final_lines: List[str] = []
    report: List[str] = []

    for item in scaled_struct:
        ingredient_line = item.get("ingredient_description") or item.get("food_name") or ""

        # 1) LLM classification + flags (classification only)
        llm_out = classify_and_flag_with_llm(
            ingredient_line=ingredient_line,
            candidates=candidates,
            model=model,
        )

        category_id = llm_out.get("category_id") or "other_unknown"
        canonical_name = llm_out.get("canonical_name") or (item.get("food_name") or ingredient_line)
        flags = _ensure_all_flags(llm_out.get("flags") or {})

        out_item = dict(item)
        out_item["mapped_category_id"] = category_id
        out_item["final_category_id"] = category_id
        out_item["food_name"] = canonical_name
        out_item["flags"] = flags

        # 2) deterministic engine with safe fallback
        out_item, out_rep = _apply_constraints_for_item(
            rules=rules,
            candidates=candidates,
            item=out_item,
            flags=out_item["flags"],
            constraints=constraints,
            prefix=prefix,
            model=model,
            state=state,
        )

        final_struct.append(out_item)
        final_lines.append(_format_final_line(out_item))
        report.extend(out_rep)

    return {
        "final_struct": final_struct,
        "final_ingredients": final_lines,
        "substitution_report": report,
    }
