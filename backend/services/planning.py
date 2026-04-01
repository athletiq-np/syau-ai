"""Scene planning and breakdown service using Qwen2.5."""
import json
import structlog
from uuid import UUID

from core.config import settings
from inference.handlers.qwen_chat import QwenChatHandler
from inference.model_cache import get_model
from inference import remote_client
from schemas.planning import ScenePlanSchema, PromptPackageSchema

log = structlog.get_logger()

SCENE_PLANNING_PROMPT = """You are a screenplay planning engine.
Return ONLY valid JSON.
No markdown. No explanation. No text before or after.

Given a scene description, break it down into:
1. scene_summary: one-line summary
2. characters: list of character names
3. location: where it takes place
4. beats: story beats in sequence (id, description)
5. shots: shots to generate (id, beat_id, shot_type, subject)

Shot types:
- t2v: text-to-video (first shot, no reference image needed)
- i2v: image-to-video (uses previous shot's last frame as reference for continuity)

Schema:
{{
  "scene_summary": "string",
  "characters": ["string"],
  "location": "string",
  "beats": [
    {{"id": "string", "description": "string"}}
  ],
  "shots": [
    {{"id": "string", "beat_id": "string", "shot_type": "t2v|i2v", "subject": "string"}}
  ]
}}

Rules:
- First shot is always t2v (no reference available yet)
- Subsequent shots can be i2v if character continues (use previous last frame)
- Each shot has a subject (what to focus on)
- Beats and shots must be in sequence
- Return ONLY the JSON, nothing else"""


def plan_scene(scene_text: str) -> ScenePlanSchema:
    """
    Parse a scene description into structured beats and shots.

    Args:
        scene_text: Raw scene description from user

    Returns:
        ScenePlanSchema with beats and shots ready for generation

    Raises:
        ValueError: If planning fails or JSON is invalid
    """
    log.info("scene_planning_started", scene_length=len(scene_text), mode=settings.inference_mode)

    if settings.inference_mode.lower() == "remote":
        result = remote_client.infer_chat(
            model=settings.llm_planner_model,
            prompt=scene_text,
            negative_prompt="",
            params={
                "system_prompt": SCENE_PLANNING_PROMPT,
            }
        )
        response_text = result["text"]
    else:
        handler = QwenChatHandler()
        model = get_model(settings.llm_planner_model, handler)

        result = handler.infer(
            model,
            inputs={"prompt": scene_text},
            params={
                "system_prompt": SCENE_PLANNING_PROMPT,
            }
        )
        response_text = result["text"]

    # Extract JSON from response (in case there's text around it)
    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")

        json_str = response_text[json_start:json_end]
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        log.error("planning_json_parse_failed", error=str(e), response=response_text[:500])
        raise ValueError(f"Failed to parse planning response as JSON: {e}")

    # Validate against schema
    try:
        plan = ScenePlanSchema(**parsed)
    except Exception as e:
        log.error("planning_schema_validation_failed", error=str(e))
        raise ValueError(f"Planning response doesn't match schema: {e}")

    log.info(
        "scene_planning_complete",
        beat_count=len(plan.beats),
        shot_count=len(plan.shots),
    )

    return plan


def assemble_shot_prompt(
    shot_subject: str,
    beat_description: str,
    scene_summary: str,
    characters: list[str],
    location: str,
) -> PromptPackageSchema:
    """
    Assemble a detailed cinematic prompt for Wan generation.

    Args:
        shot_subject: What/who is the focus
        beat_description: What happens in this beat
        scene_summary: Overall scene context
        characters: Characters in scene
        location: Where it takes place

    Returns:
        PromptPackageSchema ready for Wan T2V/I2V
    """
    # Build rich cinematic prompt
    character_str = ", ".join(characters) if characters else "Figure"

    prompt = f"""{shot_subject}.
Context: {beat_description}.
Scene: {scene_summary}.
Location: {location}.
Cinematic, moody lighting, realistic, 4K quality."""

    negative_prompt = "blurry, low quality, distorted, cartoon, amateur"

    return PromptPackageSchema(
        shot_id="",  # Will be set by caller
        shot_type="t2v",  # Will be overridden by caller
        prompt=prompt,
        negative_prompt=negative_prompt,
        duration_frames=81,
        seed=0,
    )
