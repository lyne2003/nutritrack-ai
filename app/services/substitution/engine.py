from __future__ import annotations
from typing import Dict, List, Any, Tuple

from app.services.substitution.mapper_stub import map_ingredient_to_category_stub


def _to_float(x):
    try:
        return float(str(x))
    except Exception:
        return None


def _fmt(x: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _build_line(item: Dict[str, Any]) -> str:
    amount = item.get("scaled_number_of_units")
    unit = (item.get("measurement_description") or "").strip()
    name = (item.get("food_name") or item.get("ingredient_description") or "ingredient").strip()
    if amount is None:
        return name
    if unit:
        return f"{amount} {unit} {name}".strip()
    return f"{amount} {name}".strip()


def _apply_amount_policy(amount: float, policy: str) -> float:
    if policy == "keep_same":
        return amount
    if policy == "butter_to_olive_oil_0p75":
        return amount * 0.75
    return amount


def apply_substitution(
    scaled_struct: List[Dict[str, Any]],
    constraints: Dict[str, Any],
    rules_data: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    constraints example:
    {
      "diet": ["high_protein","low_fat"],
      "allergies": ["wheat_gluten","dairy"],
      "labs": ["CREATININE_HIGH"]
    }
    """
    diet = constraints.get("diet") or []
    allergies = constraints.get("allergies") or []
    labs = constraints.get("labs") or []

    report: List[str] = []
    final_struct: List[Dict[str, Any]] = []

    for ing in scaled_struct:
        original_line = _build_line(ing)
        category_id = map_ingredient_to_category_stub(original_line, rules_data)

        if not category_id:
            final_struct.append(ing)
            report.append(f"[Step3] NO MAP: kept '{original_line}' (no category match)")
            continue

        cat_rules = (rules_data.get("rules") or {}).get(category_id, {})
        categories = rules_data.get("categories") or {}

        # Helpers
        def substitute_to(to_category: str, new_amount: str | None = None):
            tgt = categories.get(to_category, {})
            new_ing = dict(ing)
            new_ing["mapped_category_id"] = category_id
            new_ing["final_category_id"] = to_category
            # update name to target label (clean)
            new_ing["food_name"] = tgt.get("label") or new_ing.get("food_name")
            if new_amount is not None:
                new_ing["scaled_number_of_units"] = new_amount
            return new_ing

        def reduce_amount(ratio: float):
            new_ing = dict(ing)
            new_ing["mapped_category_id"] = category_id
            new_ing["final_category_id"] = category_id
            amt = _to_float(new_ing.get("scaled_number_of_units"))
            if amt is None:
                return new_ing, False
            new_amt = _fmt(amt * (1 - ratio))
            new_ing["scaled_number_of_units"] = new_amt
            return new_ing, True

        def increase_amount(ratio: float):
            new_ing = dict(ing)
            new_ing["mapped_category_id"] = category_id
            new_ing["final_category_id"] = category_id
            amt = _to_float(new_ing.get("scaled_number_of_units"))
            if amt is None:
                return new_ing, False
            new_amt = _fmt(amt * (1 + ratio))
            new_ing["scaled_number_of_units"] = new_amt
            return new_ing, True

        applied = False

        # 1) ALLERGIES (hard bans)
        allergy_rules = cat_rules.get("allergies", {})
        for a in allergies:
            r = allergy_rules.get(a)
            if not r:
                continue
            if r["action"] == "substitute_category":
                to_cat = r["to_category"]
                amt = _to_float(ing.get("scaled_number_of_units"))
                if amt is None:
                    final_struct.append(substitute_to(to_cat))
                    report.append(f"[Step3] Allergy({a}): substituted '{original_line}' -> {to_cat} (amount unchanged - not numeric)")
                else:
                    policy = r.get("amount_policy", "keep_same")
                    new_amt = _fmt(_apply_amount_policy(amt, policy))
                    final_struct.append(substitute_to(to_cat, new_amt))
                    report.append(f"[Step3] Allergy({a}): substituted '{original_line}' -> {to_cat} (amount policy={policy})")
                applied = True
                break
        if applied:
            continue

        # 2) HALAL (hard bans) — will be added in dataset later; engine already supports it
        halal_rules = cat_rules.get("halal", {})
        # (not used in this example)

        # 3) LABS (safety)
        lab_rules = cat_rules.get("labs", {})
        for lf in labs:
            r = lab_rules.get(lf)
            if not r:
                continue
            if r["action"] == "reduce_amount":
                new_ing, ok = reduce_amount(r["reduce_ratio"])
                final_struct.append(new_ing)
                report.append(f"[Step3] Lab({lf}): reduced '{original_line}' by {int(r['reduce_ratio']*100)}% ({r.get('reason','')})")
                applied = True
                break
            if r["action"] == "block_high_protein_increase":
                # we don't change here; we just set a marker so diets don't increase it
                new_ing = dict(ing)
                new_ing["mapped_category_id"] = category_id
                new_ing["final_category_id"] = category_id
                new_ing["_block_high_protein_increase"] = True
                final_struct.append(new_ing)
                report.append(f"[Step3] Lab({lf}): kept '{original_line}' and blocked protein increase ({r.get('reason','')})")
                applied = True
                break
            if r["action"] == "substitute_category":
                to_cat = r["to_category"]
                amt = _to_float(ing.get("scaled_number_of_units"))
                if amt is None:
                    final_struct.append(substitute_to(to_cat))
                    report.append(f"[Step3] Lab({lf}): substituted '{original_line}' -> {to_cat}")
                else:
                    policy = r.get("amount_policy", "keep_same")
                    new_amt = _fmt(_apply_amount_policy(amt, policy))
                    final_struct.append(substitute_to(to_cat, new_amt))
                    report.append(f"[Step3] Lab({lf}): substituted '{original_line}' -> {to_cat} (policy={policy})")
                applied = True
                break
        if applied:
            continue

        # 4) DIETS (preferences)
        diet_rules = cat_rules.get("diets", {})
        for d in diet:
            r = diet_rules.get(d)
            if not r:
                continue

            # respect lab blocks
            if d == "high_protein" and ing.get("_block_high_protein_increase"):
                final_struct.append(ing)
                report.append(f"[Step3] Diet(high_protein): skipped increase for '{original_line}' due to lab safety block")
                applied = True
                break

            if r["action"] == "reduce_amount":
                new_ing, ok = reduce_amount(r["reduce_ratio"])
                final_struct.append(new_ing)
                report.append(f"[Step3] Diet({d}): reduced '{original_line}' by {int(r['reduce_ratio']*100)}% ({r.get('reason','')})")
                applied = True
                break
            if r["action"] == "increase_amount":
                new_ing, ok = increase_amount(r["increase_ratio"])
                final_struct.append(new_ing)
                report.append(f"[Step3] Diet({d}): increased '{original_line}' by {int(r['increase_ratio']*100)}% ({r.get('reason','')})")
                applied = True
                break
            if r["action"] == "substitute_category":
                to_cat = r["to_category"]
                amt = _to_float(ing.get("scaled_number_of_units"))
                if amt is None:
                    final_struct.append(substitute_to(to_cat))
                else:
                    policy = r.get("amount_policy", "keep_same")
                    new_amt = _fmt(_apply_amount_policy(amt, policy))
                    final_struct.append(substitute_to(to_cat, new_amt))
                report.append(f"[Step3] Diet({d}): substituted '{original_line}' -> {to_cat} ({r.get('reason','')})")
                applied = True
                break

        if applied:
            continue

        # No rule applied
        final_struct.append(ing)
        report.append(f"[Step3] No change: '{original_line}' mapped to {category_id} but no applicable rule")

    return final_struct, report
