from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class IngredientStruct(BaseModel):
    food_name: str
    ingredient_description: str
    measurement_description: Optional[str] = None
    scaled_number_of_units: Optional[str] = None
    number_of_units: Optional[str] = None


class SubstitutionRequest(BaseModel):
    scaled_struct: List[Dict[str, Any]]
    diets: Optional[List[str]] = []
    allergies: Optional[List[str]] = []
    lab_flags: Optional[List[str]] = []
