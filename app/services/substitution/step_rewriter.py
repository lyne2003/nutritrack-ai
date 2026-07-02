from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gpt-4.1-mini"


def _build_substitution_map(
    scaled_struct: List[Dict[str, Any]],
    final_struct: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Build a mapping of {original_food_name -> substitute_food_name}
    by comparing the pre-substitution scaled_struct with the post-substitution final_struct.
    Only includes entries where the food_name actually changed.
    """
    sub_map: Dict[str, str] = {}

    for original, final in zip(scaled_struct, final_struct):
        orig_name = (
            original.get("food_name")
            or original.get("ingredient_description")
            or ""
        ).strip().lower()

        final_name = (final.get("food_name") or "").strip().lower()

        if orig_name and final_name and orig_name != final_name:
            sub_map[orig_name] = final_name

    return sub_map


def _apply_text_substitutions(steps: List[str], sub_map: Dict[str, str]) -> List[str]:
    """
    Apply case-insensitive whole-word/phrase substitutions to each step string.
    Longer keys are replaced first to avoid partial-match issues.
    """
    if not sub_map:
        return steps

    # Sort by length descending so longer phrases are replaced before shorter ones
    sorted_keys = sorted(sub_map.keys(), key=len, reverse=True)

    rewritten: List[str] = []
    for step in steps:
        text = step
        for orig in sorted_keys:
            replacement = sub_map[orig]
            # Case-insensitive replacement preserving word boundaries
            pattern = re.compile(re.escape(orig), re.IGNORECASE)
            text = pattern.sub(replacement, text)
        rewritten.append(text)

    return rewritten


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def _llm_polish_steps(
    steps: List[str],
    sub_map: Dict[str, str],
    recipe_name: str,
    model: str = DEFAULT_MODEL,
) -> List[str]:
    """
    Use GPT to polish the rewritten steps so they read naturally after substitution.
    Sends all steps in a single call to minimize cost.
    Returns the polished steps list (same length as input).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing in environment/.env")

    client = OpenAI(api_key=api_key)

    substitutions_summary = "\n".join(
        [f"  - '{orig}' was replaced with '{sub}'" for orig, sub in sub_map.items()]
    )

    steps_json = json.dumps(steps, ensure_ascii=False, indent=2)

    prompt = f"""You are a recipe editor. The following recipe steps have had ingredient substitutions applied.
Your job is to lightly rewrite the steps so they read naturally with the new ingredients.

Recipe name: {recipe_name or "N/A"}

Substitutions made:
{substitutions_summary}

Current steps (after text replacement):
{steps_json}

Rules:
- Fix any grammatically awkward phrases caused by the substitution (e.g., "melt the olive oil" → "heat the olive oil").
- Do NOT change the cooking method, quantities, temperatures, or timing.
- Do NOT add or remove steps.
- Keep the same number of steps.
- Return ONLY a valid JSON array of strings (one string per step), no extra text.

Return format:
["step 1 text", "step 2 text", ...]
""".strip()

    print(f"✍️  [StepRewriter] Polishing {len(steps)} step(s) with LLM ({model})...")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = resp.choices[0].message.content or ""
    text = _strip_code_fences(raw)

    try:
        polished = json.loads(text)
        if isinstance(polished, list) and len(polished) == len(steps):
            return [str(s).strip() for s in polished]
        else:
            print(f"✍️  [StepRewriter] LLM returned wrong number of steps ({len(polished)} vs {len(steps)}). Using text-replaced version.")
            return steps
    except Exception as e:
        print(f"✍️  [StepRewriter] LLM polish failed ({e}). Using text-replaced version.")
        return steps


def rewrite_steps_with_substitutions(
    steps: List[str],
    scaled_struct: List[Dict[str, Any]],
    final_struct: List[Dict[str, Any]],
    recipe_name: Optional[str] = None,
    use_llm_polish: bool = True,
    model: str = DEFAULT_MODEL,
) -> List[str]:
    """
    Rewrite recipe steps to reflect ingredient substitutions made in Step 3.

    Args:
        steps:          Original recipe direction strings from FatSecret.
        scaled_struct:  Ingredient structs BEFORE substitution (Step 2 output).
        final_struct:   Ingredient structs AFTER substitution (Step 3 output).
        recipe_name:    Optional recipe name for LLM context.
        use_llm_polish: If True, use LLM to polish the rewritten steps for natural language.
        model:          OpenAI model to use for polishing.

    Returns:
        List of rewritten step strings (same length as input steps).
    """
    if not steps:
        return steps

    # Build substitution map
    sub_map = _build_substitution_map(scaled_struct, final_struct)

    if not sub_map:
        print("✍️  [StepRewriter] No substitutions detected — steps unchanged.")
        return steps

    print(f"✍️  [StepRewriter] Substitution map: {sub_map}")

    # Tier 1: deterministic text replacement
    rewritten = _apply_text_substitutions(steps, sub_map)

    # Tier 2: LLM polish (optional)
    if use_llm_polish:
        rewritten = _llm_polish_steps(rewritten, sub_map, recipe_name or "", model)

    return rewritten
