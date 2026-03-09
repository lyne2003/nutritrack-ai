# app/services/scaling/scaler.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional


FRACTION_RE = re.compile(r"^\d+\s*/\s*\d+$")
MIXED_FRACTION_RE = re.compile(r"^\d+\s+\d+\s*/\s*\d+$")


def _parse_amount(token: str) -> Optional[float]:
    """
    Parses:
      - "2" -> 2.0
      - "2.5" -> 2.5
      - "1/2" -> 0.5
      - "1 1/2" -> 1.5
    Returns None if not parseable.
    """
    t = token.strip()

    # mixed fraction: "1 1/2"
    if MIXED_FRACTION_RE.match(t):
        whole, frac = t.split(maxsplit=1)
        num, den = frac.split("/")
        return float(whole) + (float(num) / float(den))

    # simple fraction: "1/2"
    if FRACTION_RE.match(t):
        num, den = t.split("/")
        return float(num) / float(den)

    # decimal / int
    try:
        return float(t)
    except ValueError:
        return None


def _format_amount(x: float) -> str:
    """
    Format scaled amount nicely:
    - avoid trailing .0
    - keep up to 2 decimals when needed
    """
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".")


@dataclass
class ScaleResult:
    scaled_ingredients: List[str]
    report: List[str]  # human-readable notes


def scale_ingredient_lines(
    ingredient_lines: List[str],
    base_servings: float,
    user_servings: float,
) -> ScaleResult:
    """
    Scales ingredient lines that START with a quantity.
    If a line doesn't start with a parseable quantity, keep it unchanged and note it in report.
    """
    report: List[str] = []

    if base_servings <= 0 or user_servings <= 0:
        raise ValueError("base_servings and user_servings must be > 0")

    factor = user_servings / base_servings

    scaled: List[str] = []
    for line in ingredient_lines:
        raw = line.strip()
        if not raw:
            continue

        parts = raw.split()

        # Try first token, or first two tokens as mixed fraction.
        amt = _parse_amount(parts[0])
        amt_tokens_used = 1

        if amt is None and len(parts) >= 2:
            maybe_mixed = parts[0] + " " + parts[1]
            amt2 = _parse_amount(maybe_mixed)
            if amt2 is not None:
                amt = amt2
                amt_tokens_used = 2

        if amt is None:
            scaled.append(raw)
            report.append(f"UNCHANGED (no amount): {raw}")
            continue

        new_amt = amt * factor
        new_amt_str = _format_amount(new_amt)

        remainder = " ".join(parts[amt_tokens_used:])
        new_line = (new_amt_str + " " + remainder).strip()

        scaled.append(new_line)
        report.append(f"SCALED: '{raw}' -> '{new_line}'")

    report.insert(0, f"Scale factor = {user_servings}/{base_servings} = {factor:.4f}")
    return ScaleResult(scaled_ingredients=scaled, report=report)
