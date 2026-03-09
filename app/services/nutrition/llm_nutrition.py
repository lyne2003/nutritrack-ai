from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = "gpt-4.1-mini"


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def _safe_float(x: Any, fallback: float = 0.0) -> float:
    try:
        if x is None:
            return fallback
        return float(x)
    except Exception:
        return fallback


def _normalize_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure numeric fields exist and are non-negative.
    """
    per_serving = data.get("per_serving") or {}
    totals = data.get("totals") or {}
    meta = data.get("meta") or {}

    # required per-serving
    out_per = {
        "calories_kcal": max(0.0, _safe_float(per_serving.get("calories_kcal"))),
        "protein_g": max(0.0, _safe_float(per_serving.get("protein_g"))),
        "carbs_g": max(0.0, _safe_float(per_serving.get("carbs_g"))),
        "fat_g": max(0.0, _safe_float(per_serving.get("fat_g"))),
        "fiber_g": None if per_serving.get("fiber_g") is None else max(0.0, _safe_float(per_serving.get("fiber_g"))),
        "sugars_g": None if per_serving.get("sugars_g") is None else max(0.0, _safe_float(per_serving.get("sugars_g"))),
        "sodium_mg": None if per_serving.get("sodium_mg") is None else max(0.0, _safe_float(per_serving.get("sodium_mg"))),
    }

    # totals (optional, but we keep it for transparency)
    out_totals = {
        "calories_kcal": max(0.0, _safe_float(totals.get("calories_kcal"))),
        "protein_g": max(0.0, _safe_float(totals.get("protein_g"))),
        "carbs_g": max(0.0, _safe_float(totals.get("carbs_g"))),
        "fat_g": max(0.0, _safe_float(totals.get("fat_g"))),
        "fiber_g": None if totals.get("fiber_g") is None else max(0.0, _safe_float(totals.get("fiber_g"))),
        "sugars_g": None if totals.get("sugars_g") is None else max(0.0, _safe_float(totals.get("sugars_g"))),
        "sodium_mg": None if totals.get("sodium_mg") is None else max(0.0, _safe_float(totals.get("sodium_mg"))),
    }

    out_meta = {
        "is_estimate": bool(meta.get("is_estimate", True)),
        "notes": [str(x).strip() for x in (meta.get("notes") or []) if str(x).strip()],
        "confidence": str(meta.get("confidence") or "medium").strip().lower(),
    }

    return {"per_serving": out_per, "totals": out_totals, "meta": out_meta}


def compute_nutrition_per_serving_with_llm(
    final_ingredients: List[str],
    servings: float,
    recipe_name: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Step 4 (Nutrition):
    Input: final ingredient lines WITH measurements (post-step3) + servings
    Output: nutrition totals + per-serving nutrition (estimated).
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing in environment/.env")

    client = OpenAI(api_key=api_key)

    title = (recipe_name or "").strip()
    ingredients_block = "\n".join([f"- {line.strip()}" for line in final_ingredients if line.strip()])

    prompt = f"""
You are a nutrition estimation engine.

Task:
Given a recipe ingredient list with measurements, estimate TOTAL nutrition for the whole recipe,
then compute PER-SERVING nutrition by dividing by servings.

Recipe name (optional): {title if title else "N/A"}
Servings: {servings}

Ingredients (final, with measurements):
{ingredients_block}

Rules:
- Output MUST be valid JSON (no extra text).
- Use realistic nutrition estimates (not perfect; indicate estimate).
- If an ingredient is ambiguous, choose the most common interpretation and add a note.
- Return calories in kcal, macros in grams, sodium in mg.
- Keep all numbers >= 0.

Return JSON with exactly this structure:
{{
  "totals": {{
    "calories_kcal": number,
    "protein_g": number,
    "carbs_g": number,
    "fat_g": number,
    "fiber_g": number|null,
    "sugars_g": number|null,
    "sodium_mg": number|null
  }},
  "per_serving": {{
    "calories_kcal": number,
    "protein_g": number,
    "carbs_g": number,
    "fat_g": number,
    "fiber_g": number|null,
    "sugars_g": number|null,
    "sodium_mg": number|null
  }},
  "meta": {{
    "is_estimate": true,
    "confidence": "low"|"medium"|"high",
    "notes": [string, ...]
  }}
}}
""".strip()

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = resp.choices[0].message.content or ""
    text = _strip_code_fences(raw)

    try:
        data = json.loads(text)
    except Exception:
        # Fallback safe result
        data = {
            "totals": {"calories_kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": None, "sugars_g": None, "sodium_mg": None},
            "per_serving": {"calories_kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": None, "sugars_g": None, "sodium_mg": None},
            "meta": {"is_estimate": True, "confidence": "low", "notes": ["LLM returned non-JSON; fallback zeros used."]},
        }

    # Normalize + enforce numeric safety
    return _normalize_result(data)
