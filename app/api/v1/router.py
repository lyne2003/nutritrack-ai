from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.cv import router as cv_router
from app.api.v1.endpoints import fatsecret
from app.api.v1.endpoints import scale
from app.api.v1.endpoints import substitution
from app.api.v1.endpoints import nutrition
from app.api.v1.endpoints import pipeline_test
from app.api.v1.endpoints import generate

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(cv_router, prefix="/cv", tags=["cv"])

router.include_router(fatsecret.router, tags=["fatsecret"])

router.include_router(scale.router, tags=["scale"])

router.include_router(substitution.router, tags=["substitution"])

router.include_router(nutrition.router, tags=["nutrition"])

router.include_router(pipeline_test.router, tags=["pipeline"])
router.include_router(generate.router, tags=["generate"])