from fastapi import APIRouter, UploadFile, File, HTTPException
from api.services.onnx_inference import onnx_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def _calculate_severity(confidence: float) -> str:
    if confidence > 0.9:
        return "critical"
    if confidence > 0.7:
        return "high"
    if confidence > 0.5:
        return "medium"
    return "low"

@router.post("/detect")
async def detect_fire(image: UploadFile = File(...)):
    """
    Run ONNX inference on an uploaded image.
    Returns top-level 'detected', 'confidence', and 'severity' so the Flutter
    app can read them directly without extra nesting.
    """
    try:
        image_bytes = await image.read()

        # Run inference using the service
        results = await onnx_service.run_inference(image_bytes)

        detected: bool = results.get("detected", False)
        confidence: float = float(results.get("confidence", 0.0))
        severity: str = results.get("severity") or _calculate_severity(confidence)

        return {
            "status": "success",
            # Flat fields that Flutter camera_screen.dart reads directly
            "detected": detected,
            "confidence": confidence,
            "severity": severity,
            "timestamp": results.get("timestamp", ""),
            # Full result for debugging / future use
            "results": results,
            "filename": image.filename
        }
    except Exception as e:
        logger.error(f"Inference API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

