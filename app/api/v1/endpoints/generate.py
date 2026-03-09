from fastapi import APIRouter
from app.schemas.generate import GenerateRequest
from app.services.pipeline.generator import generate_two_recipes_full_pipeline

router = APIRouter()


@router.post("/generate")
def generate(req: GenerateRequest):
    recipes = generate_two_recipes_full_pipeline(
        ingredients_str=req.ingredients,
        servings=req.servings,
        diets=req.diets,
        allergies=req.allergies,
        lab_flags=req.lab_flags,
    )
    return {"ok": True, "data": {"recipes": recipes}, "error": None}
