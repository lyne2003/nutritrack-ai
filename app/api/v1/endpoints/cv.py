from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, Query
from fastapi.responses import JSONResponse

from app.services.cv.yolo import detect_image_bytes, dedupe_labels

router = APIRouter()


@router.post("/detect")
async def detect_cv(
    images: list[UploadFile] = File(..., description="One or many images. Field name must be 'images'."),
    conf_threshold: float = Query(0.25, ge=0.0, le=1.0),
    iou_threshold: float = Query(0.45, ge=0.0, le=1.0),
    max_det: int = Query(50, ge=1, le=300),
    max_images: int = Query(10, ge=1, le=50),
):
    """
    Receives 1+ images, runs YOLO on each, merges detections, returns a single deduped list.
    Final output contains NO confidence values (by design).
    """
    if not images or len(images) == 0:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "data": None,
                "error": {
                    "code": "NO_IMAGES",
                    "message": "No images were provided. Use form field 'images'.",
                },
            },
        )

    if len(images) > max_images:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "data": None,
                "error": {
                    "code": "TOO_MANY_IMAGES",
                    "message": f"Too many images. Max allowed is {max_images}.",
                },
            },
        )

    all_labels: list[str] = []

    for img in images:
        image_bytes = await img.read()
        dets = detect_image_bytes(
            image_bytes=image_bytes,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            max_det=max_det,
        )
        all_labels.extend([d.label for d in dets])

    deduped = dedupe_labels(all_labels)

    return {
        "ok": True,
        "data": {"deduped_ingredients": deduped},
        "error": None,
    }
