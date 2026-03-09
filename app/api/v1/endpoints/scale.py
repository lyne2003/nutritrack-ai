from fastapi import APIRouter
from app.schemas.scaling import ScaleRequest
from app.services.scaling.structured_scaler import scale_structured_ingredients

router = APIRouter()

@router.post("/scale")
def scale_endpoint(payload: ScaleRequest):
    res = scale_structured_ingredients(
        ingredients_struct=[x.model_dump() for x in payload.ingredients_struct],
        base_servings=payload.base_servings,
        user_servings=payload.user_servings,
    )
    return {
        "ok": True,
        "data": {
            "scaled_ingredients": res.scaled_lines,
            "scaling_report": res.report,
            "scaled_struct": res.scaled_struct,
        },
        "error": None,
    }
