from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class NutritionTestRequest(BaseModel):
    # from Step 3
    final_ingredients: List[str] = Field(..., min_length=1)

    # user servings (the servings the user asked for)
    servings: float = Field(..., gt=0)

    # optional: recipe name just for better prompting / logging
    recipe_name: Optional[str] = None


class NutritionFacts(BaseModel):
    # per serving
    calories_kcal: float = Field(..., ge=0)
    protein_g: float = Field(..., ge=0)
    carbs_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)

    # optional extras (nice to have)
    fiber_g: Optional[float] = Field(default=None, ge=0)
    sugars_g: Optional[float] = Field(default=None, ge=0)
    sodium_mg: Optional[float] = Field(default=None, ge=0)


class NutritionTestResponse(BaseModel):
    ok: bool
    data: Dict[str, Any]
    error: Optional[str] = None
