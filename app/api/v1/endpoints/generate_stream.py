from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.generate import GenerateRequest
from app.services.pipeline.generator_stream import stream_recipe_pipeline

router = APIRouter()


@router.post("/generate/stream")
async def generate_stream(req: GenerateRequest):
    """
    SSE endpoint — streams progress events then the final recipe.

    Each event is a JSON line:
      data: {"type": "progress", "message": "..."}
      data: {"type": "done", "recipe": {...}}
      data: {"type": "error", "message": "..."}
    """
    print("🔥 [STREAM] REQUEST RECEIVED")
    print("Ingredients:", req.ingredients)
    print("Servings:", req.servings)
    print("Diets:", req.diets)
    print("Allergies:", req.allergies)
    print("Lab Flags:", req.lab_flags)

    return StreamingResponse(
        stream_recipe_pipeline(
            ingredients_str=req.ingredients,
            servings=req.servings,
            diets=req.diets,
            allergies=req.allergies,
            lab_flags=req.lab_flags,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
