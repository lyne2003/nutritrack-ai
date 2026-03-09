from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


DEFAULT_MODEL = "gpt-4.1-mini"

ALL_FLAGS = [
    # Allergies
    "contains_wheat_gluten",
    "contains_dairy",
    "contains_egg",
    "contains_fish",
    "contains_soy",
    "contains_tree_nut",
    "contains_peanut",
    "contains_sesame",

    # Diet friendliness
    "is_vegan_friendly",
    "is_vegetarian_friendly",
    "is_gluten_free_friendly",

    # Halal: use violation flag for clean rule triggering
    "violates_halal",

    # Diet risk
    "is_low_carb_risky",
    "is_low_fat_risky",
    "is_low_sodium_risky",
    "is_high_protein_source",

    # Labs triggers
    "raises_ldl_risk",
    "raises_triglycerides_risk",
    "raises_glucose_risk",
    "kidney_risky_high_sodium",
    "kidney_risky_very_high_protein",

    # Meta
    "is_processed",
    "is_added_sugar",
    "is_refined_carb",
]


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def _compact_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for c in candidates:
        out.append({
            "category_id": c.get("category_id"),
            "label": c.get("label"),
            "examples": (c.get("examples") or [])[:8],
        })
    return out


def _build_classifier_prompt(ingredient_line: str, candidates: List[Dict[str, Any]]) -> str:
    compact = _compact_candidates(candidates)
    schema_flags = ", ".join([f'"{k}": true/false' for k in ALL_FLAGS])

    # Clear definitions improve consistency
    definitions = """
Flag definitions (be conservative for allergens):
- contains_wheat_gluten: true if wheat/barley/rye/bulgur/couscous/semolina/malt/gluten is present.
- contains_dairy: true if milk/cream/butter/ghee/cheese/yogurt/whey/casein is present.
- contains_egg: true if egg/egg white/egg yolk/mayo/egg-based noodles are clearly present.
- contains_fish: true if fish/seafood/fish sauce/anchovy-based ingredients are present.
- contains_soy: true if soy/tofu/soy sauce/miso/edamame is present.
- contains_tree_nut / contains_peanut / contains_sesame: true if clearly present.
- violates_halal: true if clearly pork, alcohol in cooking, or non-halal meat/gelatin is implied.

Diet friendliness:
- is_vegan_friendly: true only if it contains no animal products.
- is_vegetarian_friendly: true if no meat/fish; dairy/eggs allowed.
- is_gluten_free_friendly: true if no gluten grains/derivatives.

Diet risk:
- is_low_carb_risky: true for refined grains, rice, potatoes, sugars.
- is_low_fat_risky: true for butter/cream/cheese/heavy oils/fried fats.
- is_low_sodium_risky: true for salt, bouillon, soy sauce, processed sauces/meats.
- is_high_protein_source: true for meat/fish/eggs/tofu/legumes.

Labs:
- raises_ldl_risk: high saturated fat/trans fat foods (butter, ghee, fatty cheese, processed meats).
- raises_triglycerides_risk: added sugars + refined carbs heavy.
- raises_glucose_risk: sugars + refined carbs/high-GI starches.
- kidney_risky_high_sodium: salt/bouillon/soy sauce/processed sauces.
- kidney_risky_very_high_protein: protein powders/concentrates or extreme protein products.
"""

    return (
        "You are an ingredient analyzer for a nutrition assistant.\n"
        "Task:\n"
        "1) Choose EXACTLY ONE category_id from the provided candidates.\n"
        "2) Produce a canonical_name (what the ingredient is, without quantities/units/brands).\n"
        "3) Answer ALL boolean flags.\n\n"
        "Hard rules:\n"
        "- category_id MUST be one of the candidates. Do NOT invent new ids.\n"
        "- canonical_name must match the ingredient (do NOT change it to another food).\n"
        "- flags must be booleans (true/false) for ALL keys.\n"
        "- Be conservative for allergens.\n\n"
        f"{definitions}\n\n"
        f"Ingredient line:\n{ingredient_line}\n\n"
        "Candidates:\n"
        f"{json.dumps(compact, ensure_ascii=False, indent=2)}\n\n"
        "Return STRICT JSON ONLY with this schema:\n"
        "{\n"
        '  "category_id": "string",\n'
        '  "canonical_name": "string",\n'
        '  "flags": {\n'
        f"    {schema_flags}\n"
        "  }\n"
        "}\n"
    )


def classify_and_flag_with_llm(
    ingredient_line: str,
    candidates: List[Dict[str, Any]],
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing (set it in .env or terminal env)")

    # Safe fallback if no candidates (should not happen once we pass all categories)
    if not candidates:
        flags = {k: False for k in ALL_FLAGS}
        return {"category_id": "other_unknown", "canonical_name": ingredient_line.strip(), "flags": flags}

    allowed = {c.get("category_id") for c in candidates if c.get("category_id")}
    client = OpenAI(api_key=api_key)
    prompt = _build_classifier_prompt(ingredient_line, candidates)

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
        top = candidates[0]
        flags = {k: False for k in ALL_FLAGS}
        return {"category_id": top.get("category_id"), "canonical_name": ingredient_line.strip(), "flags": flags}

    if data.get("category_id") not in allowed:
        data["category_id"] = candidates[0].get("category_id")

    if not isinstance(data.get("canonical_name"), str) or not data["canonical_name"].strip():
        data["canonical_name"] = ingredient_line.strip()

    flags_in = data.get("flags") or {}
    flags_out = {k: bool(flags_in.get(k, False)) for k in ALL_FLAGS}
    data["flags"] = flags_out
    return data


# -----------------------------
# LLM fallback for missing rules
# -----------------------------
def _build_fallback_prompt(
    ingredient_line: str,
    canonical_name: str,
    category_id: str,
    triggered: List[str],
    constraints: Dict[str, Any],
    priority: List[str],
) -> str:
    return (
        "You are a nutrition substitution assistant.\n"
        "We have a deterministic ruleset, but for this ingredient the rule is missing.\n"
        "You must propose a SAFE, generic substitution or amount adjustment.\n\n"
        "Strict priority order (highest first):\n"
        f"{priority}\n\n"
        "User constraints:\n"
        f"{json.dumps(constraints, ensure_ascii=False, indent=2)}\n\n"
        "Triggered constraints for THIS ingredient:\n"
        f"{triggered}\n\n"
        "Ingredient:\n"
        f"- original_line: {ingredient_line}\n"
        f"- canonical_name: {canonical_name}\n"
        f"- category_id: {category_id}\n\n"
        "Return STRICT JSON only with this schema:\n"
        "{\n"
        '  "action": "substitute" | "reduce_amount" | "keep",\n'
        '  "substitute_name": "string or null",\n'
        '  "amount_multiplier": "number or null",\n'
        '  "reason_user": "short user-friendly reason"\n'
        "}\n\n"
        "Hard rules:\n"
        "- If an allergy is triggered, prefer action=substitute.\n"
        "- If gluten is triggered, prefer gluten-free alternatives.\n"
        "- If vegan/vegetarian is triggered, replace animal foods with tofu/legumes.\n"
        "- If low_sodium or kidney sodium is triggered, replace salty items with herbs/lemon.\n"
        "- If LDL is triggered, avoid butter/processed meats; prefer olive oil/lean proteins.\n"
        "- Keep the substitution generic and commonly available.\n"
    )


def suggest_fallback_action_with_llm(
    ingredient_line: str,
    canonical_name: str,
    category_id: str,
    triggered: List[str],
    constraints: Dict[str, Any],
    priority: List[str],
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing (set it in .env or terminal env)")

    client = OpenAI(api_key=api_key)
    prompt = _build_fallback_prompt(ingredient_line, canonical_name, category_id, triggered, constraints, priority)

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
        # safest fallback: keep
        return {"action": "keep", "substitute_name": None, "amount_multiplier": None, "reason_user": "no safe fallback found"}

    action = (data.get("action") or "keep").strip().lower()
    if action not in {"substitute", "reduce_amount", "keep"}:
        action = "keep"

    sub_name = data.get("substitute_name")
    if not isinstance(sub_name, str) or not sub_name.strip():
        sub_name = None

    mult = data.get("amount_multiplier")
    try:
        mult = float(mult) if mult is not None else None
    except Exception:
        mult = None

    reason = data.get("reason_user")
    if not isinstance(reason, str) or not reason.strip():
        reason = "it conflicts with your constraints"

    # Clean punctuation for report readability
    reason = reason.strip()
    while reason.endswith(".."):
        reason = reason[:-1]
    if reason.endswith("."):
        reason = reason[:-1]

    return {"action": action, "substitute_name": sub_name, "amount_multiplier": mult, "reason_user": reason}
