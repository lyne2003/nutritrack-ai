from fastapi import APIRouter, Query

from app.services.fatsecret.service import retrieve_two_recipes

router = APIRouter()

@router.get("/fatsecret/retrieve2")
def fatsecret_retrieve2(
    ingredients: str = Query(..., description='Example: "broccoli, tomato, pasta"'),
):
    recipes = retrieve_two_recipes(ingredients)
    return {"ok": True, "data": {"recipes": recipes}, "error": None}
