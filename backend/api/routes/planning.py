"""Planning API routes for scene breakdown and shot planning."""
from fastapi import APIRouter, HTTPException, status
import structlog

from schemas.planning import ScenePlanSchema
from services.planning import plan_scene

log = structlog.get_logger()

router = APIRouter(prefix="/api/planning", tags=["planning"])


@router.post("/scene-parse", response_model=ScenePlanSchema)
def parse_scene(scene_text: str) -> ScenePlanSchema:
    """
    Parse a scene description into beats and shots.

    Takes raw scene text and uses Qwen2.5 to break it down into:
    - Story beats (what happens)
    - Shots (what to generate)
    - Shot types (t2v for first, i2v for continuity)

    Args:
        scene_text: Scene description (e.g., "Explorer enters ruin at night...")

    Returns:
        ScenePlanSchema with beats and shots ready for generation

    Example:
        POST /api/planning/scene-parse?scene_text=Explorer%20enters%20dark%20ruin
        Returns:
        {
          "scene_summary": "Explorer discovers ancient mandala",
          "characters": ["Explorer"],
          "location": "Stone ruin",
          "beats": [...],
          "shots": [...]
        }
    """
    if not scene_text or not scene_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scene_text is required and cannot be empty"
        )

    try:
        plan = plan_scene(scene_text.strip())
        log.info(
            "api_scene_parse_success",
            beats=len(plan.beats),
            shots=len(plan.shots),
        )
        return plan
    except ValueError as e:
        log.error("api_scene_parse_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scene planning failed: {str(e)}"
        )
    except Exception as e:
        log.error("api_scene_parse_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error during scene planning"
        )
