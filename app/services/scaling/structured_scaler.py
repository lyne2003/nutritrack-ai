# app/services/scaling/structured_scaler.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _to_float(x: Any) -> Optional[float]:
    try:
        return float(str(x).strip())
    except Exception:
        return None


def _fmt(x: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".")


@dataclass
class ScaleResult:
    scaled_struct: List[Dict[str, Any]]
    scaled_lines: List[str]
    report: List[str]


def scale_structured_ingredients(
    ingredients_struct: List[Dict[str, Any]],
    base_servings: Any,   # ✅ changed: was float
    user_servings: Any,   # ✅ changed: was float
) -> ScaleResult:
    """
    Step 2 (Scaling) — Pure local scaling.
    Inputs are what we already retrieved in Step 1.
    No FatSecret calls here.
    """

    # ✅ FIX: FatSecret often returns servings as strings ("4"), so cast safely
    base_servings_f = _to_float(base_servings)
    user_servings_f = _to_float(user_servings)

    if base_servings_f is None or user_servings_f is None:
        raise ValueError(f"Invalid servings (not numeric): base_servings={base_servings} user_servings={user_servings}")

    if base_servings_f <= 0 or user_servings_f <= 0:
        raise ValueError("base_servings and user_servings must be > 0")

    factor = user_servings_f / base_servings_f
    report: List[str] = [f"Scale factor = {user_servings_f}/{base_servings_f} = {factor:.4f}"]

    scaled_struct: List[Dict[str, Any]] = []
    scaled_lines: List[str] = []

    for ing in ingredients_struct:
        units = _to_float(ing.get("number_of_units"))
        unit_name = (ing.get("measurement_description") or "").strip()
        desc = (ing.get("ingredient_description") or "").strip()
        food_name = (ing.get("food_name") or "").strip()

        label = food_name or desc or "ingredient"

        if units is None:
            # Can't scale; keep as-is
            scaled_struct.append({**ing, "scaled_number_of_units": None})
            scaled_lines.append(desc or label)
            report.append(f"UNCHANGED (invalid number_of_units): {desc or label}")
            continue

        new_units = units * factor
        new_units_s = _fmt(new_units)

        # Build display line
        if unit_name:
            line = f"{new_units_s} {unit_name} {label}".strip()
        else:
            line = f"{new_units_s} {label}".strip()

        scaled_struct.append({**ing, "scaled_number_of_units": new_units_s})
        scaled_lines.append(line)
        report.append(f"SCALED: {units} -> {new_units_s} | {desc or label}")

    return ScaleResult(scaled_struct=scaled_struct, scaled_lines=scaled_lines, report=report)
