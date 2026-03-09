from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
from pathlib import Path

from ultralytics import YOLO

from app.core.config import settings
from io import BytesIO

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bbox_xyxy: Tuple[int, int, int, int]  # (x1, y1, x2, y2)


_model: YOLO | None = None


def get_model() -> YOLO:
    """
    Lazy-load YOLO model once per process.
    """
    global _model

    if _model is not None:
        return _model

    if not settings.YOLO_MODEL_PATH:
        raise RuntimeError("YOLO_MODEL_PATH is not set. Add it to .env")

    model_path = Path(settings.YOLO_MODEL_PATH)
    if not model_path.exists():
        raise FileNotFoundError(f"YOLO model not found at: {model_path}")

    _model = YOLO(str(model_path))
    return _model


def detect_image_bytes(
    image_bytes: bytes,
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    max_det: int = 50,
) -> List[Detection]:
    """
    Run YOLO inference on a single image (bytes) and return structured detections.
    """
    model = get_model()

    # Convert bytes -> PIL -> numpy (Ultralytics supports numpy/PIL/file path)
    try:
        pil_img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(pil_img)
    except Exception as e:
        raise ValueError(f"Invalid image bytes: {e}")

    results = model.predict(
        source=img_np,
        conf=conf_threshold,
        iou=iou_threshold,
        max_det=max_det,
        verbose=False,
    )

    dets: List[Detection] = []
    if not results:
        return dets

    r0 = results[0]
    if r0.boxes is None or len(r0.boxes) == 0:
        return dets

    names = r0.names  # class_id -> label

    for b in r0.boxes:
        cls_id = int(b.cls[0].item())
        label = str(names.get(cls_id, cls_id))
        conf = float(b.conf[0].item())
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        dets.append(
            Detection(
                label=label,
                confidence=conf,
                bbox_xyxy=(int(x1), int(y1), int(x2), int(y2)),
            )
        )

    return dets



def normalize_label(label: str) -> str:
    return label.strip().lower().replace("_", " ")


def dedupe_labels(labels: List[str]) -> List[str]:
    """
    Deduplicate while keeping first-seen order.
    """
    seen = set()
    out: List[str] = []
    for x in labels:
        nx = normalize_label(x)
        if nx not in seen:
            seen.add(nx)
            out.append(nx)
    return out
