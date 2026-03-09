from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict


class GenerateRequest(BaseModel):
    # the exact string the mobile sends: "chicken, rice, broccoli"
    ingredients: str = Field(..., min_length=1)

    # required
    servings: float = Field(..., gt=0)

    # optional constraints
    diets: List[str] = Field(default_factory=list)        # lowercase strings
    allergies: List[str] = Field(default_factory=list)    # lowercase strings
    lab_flags: List[str] = Field(default_factory=list)    # UPPERCASE strings


class RecipeResult(BaseModel):
    recipe_id: Optional[str] = None
    recipe_name: str
    prep_time_min: Optional[Any] = None

    # from step1
    steps: List[str] = Field(default_factory=list)

    # final (step3)
    final_ingredients: List[str] = Field(default_factory=list)
    substitution_report: List[Dict[str, Any]] = Field(default_factory=list)

    # step4 (ONLY per serving returned)
    nutrition_per_serving: Dict[str, Any] = Field(default_factory=dict)

    # echo
    user_servings: float


class GenerateResponse(BaseModel):
    ok: bool
    data: Dict[str, Any]
    error: Optional[str] = None
