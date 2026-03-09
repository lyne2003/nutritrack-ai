# app/api/v1/schemas/scaling.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional


class IngredientStruct(BaseModel):
    food_name: Optional[str] = None
    ingredient_description: Optional[str] = None
    number_of_units: Optional[str] = None
    measurement_description: Optional[str] = None


class ScaleRequest(BaseModel):
    base_servings: float = Field(..., gt=0)
    user_servings: float = Field(..., gt=0)
    ingredients_struct: List[IngredientStruct]


class ScaleResponseData(BaseModel):
    scaled_ingredients: List[str]
    scaling_report: List[str]
    scaled_struct: List[dict]
