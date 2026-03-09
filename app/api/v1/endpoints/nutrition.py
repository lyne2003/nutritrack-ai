from fastapi import APIRouter
from app.schemas.nutrition import NutritionTestRequest
from app.services.nutrition.llm_nutrition import compute_nutrition_per_serving_with_llm

router = APIRouter()


@router.post("/nutrition/test")
def nutrition_test(req: NutritionTestRequest):
    result = compute_nutrition_per_serving_with_llm(
        final_ingredients=req.final_ingredients,
        servings=req.servings,
        recipe_name=req.recipe_name,
    )
    return {"ok": True, "data": result, "error": None}
