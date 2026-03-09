from fastapi import APIRouter
from app.schemas.substitution import SubstitutionRequest
from app.services.substitution.step3_engine import run_step3_substitution

router = APIRouter()

def _build_line(item: dict) -> str:
    amount = item.get("scaled_number_of_units")
    unit = (item.get("measurement_description") or "").strip()
    name = (item.get("food_name") or item.get("ingredient_description") or "ingredient").strip()
    if amount is None:
        return name
    if unit:
        return f"{amount} {unit} {name}".strip()
    return f"{amount} {name}".strip()

@router.post("/substitution/test")
def substitution_test(req: SubstitutionRequest):
    result = run_step3_substitution(
        scaled_struct=req.scaled_struct,
        diets=req.diets,
        allergies=req.allergies,
        lab_flags=req.lab_flags,
    )
    return {"ok": True, "data": result, "error": None}