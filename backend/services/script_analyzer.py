"""Script analyzer - breaks scripts into scenes and shots using Qwen."""
import json
import structlog
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import settings
from models.project import Project, Character, Scene, Shot, ShotType, ShotStatus
from inference.handlers.qwen_chat import QwenChatHandler
from inference.model_cache import get_model
from inference import remote_client

log = structlog.get_logger()


# Qwen script analysis prompt template
SCRIPT_ANALYSIS_PROMPT_TEMPLATE = """You are a cinematographer and screenwriter. Analyze this script and break it into scenes and shots for video generation.

Characters in this project:
{character_list}

Script:
{script}

Return ONLY valid JSON in this exact format (no markdown, no explanation, just JSON):
{{
  "scenes": [
    {{
      "title": "Scene title",
      "description": "Brief scene description",
      "shots": [
        {{
          "prompt": "Detailed cinematic prompt for video generation. Include lighting, camera angle, movement, atmosphere, mood.",
          "negative_prompt": "optional negative",
          "shot_type": "t2v",
          "duration_frames": 81,
          "characters": ["character_name"]
        }}
      ]
    }}
  ]
}}

Rules:
- Analyze each scene and break it into individual shots
- First shot of a scene: use "t2v" (text-to-video, no reference needed)
- Subsequent shots with same character: use "i2v" (image-to-video, will use previous shot's last frame)
- Make prompts cinematic and detailed (camera movement, lighting, mood, composition)
- Inject character physical descriptions into prompts naturally
- duration_frames: 81 is the standard (5 seconds at 16fps)
- Ensure prompts are rich and specific enough to generate cinematic quality video"""


def analyze_script(project_id: UUID, db: Session) -> dict[str, Any]:
    """
    Analyze a project's script and create scenes/shots.

    Returns: {
        "scenes": [
            {
                "id": UUID,
                "title": str,
                "shots": [
                    {
                        "id": UUID,
                        "prompt": str,
                        "shot_type": str,
                        ...
                    }
                ]
            }
        ]
    }
    """
    # Load project and characters
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project {project_id} not found")

    if not project.script or not project.script.strip():
        raise ValueError("Project has no script")

    characters = db.query(Character).filter(Character.project_id == project_id).all()

    # Build character list for prompt
    character_list = "\n".join([
        f"- {c.name}: {c.description}" for c in characters
    ]) or "(No characters defined yet)"

    # Build analysis prompt
    prompt = SCRIPT_ANALYSIS_PROMPT_TEMPLATE.format(
        character_list=character_list,
        script=project.script,
    )

    # Call Qwen to analyze
    log.info("script_analysis_starting", project_id=str(project_id))

    if settings.inference_mode.lower() == "remote":
        result = remote_client.infer_chat(
            model="qwen3.5-7b-instruct",
            prompt=prompt,
            negative_prompt="",
            params={
                "system_prompt": "You are a screenwriter and cinematographer. Return ONLY valid JSON with no markdown or explanation.",
            }
        )
        response_text = result["text"]
    else:
        handler = QwenChatHandler()
        qwen_model = get_model("qwen3.5-7b-instruct", handler)
        result = handler.infer(
            qwen_model,
            inputs={"prompt": prompt},
            params={
                "system_prompt": "You are a screenwriter and cinematographer. Return ONLY valid JSON with no markdown or explanation.",
            }
        )
        response_text = result["text"]

    # Parse JSON response
    try:
        # Try to extract JSON from response (in case there's text around it)
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")

        json_str = response_text[json_start:json_end]
        parsed = json.loads(json_str)
        scenes_data = parsed.get("scenes", [])
    except json.JSONDecodeError as e:
        log.error("script_analysis_json_parse_failed", error=str(e), response=response_text[:500])
        raise ValueError(f"Failed to parse Qwen response as JSON: {e}")

    if not scenes_data:
        raise ValueError("No scenes in parsed response")

    # Create database records
    created_scenes = []
    total_shots = 0

    for scene_idx, scene_data in enumerate(scenes_data):
        scene = Scene(
            project_id=project_id,
            order_index=scene_idx,
            title=scene_data.get("title", f"Scene {scene_idx + 1}"),
            description=scene_data.get("description", ""),
        )
        db.add(scene)
        db.flush()  # Get the scene ID

        shots_data = scene_data.get("shots", [])
        for shot_idx, shot_data in enumerate(shots_data):
            shot_type = shot_data.get("shot_type", "t2v")
            if shot_type not in ("t2v", "i2v"):
                shot_type = "t2v"

            shot = Shot(
                scene_id=scene.id,
                project_id=project_id,
                order_index=total_shots,
                shot_type=shot_type,
                status=ShotStatus.pending,
                prompt=shot_data.get("prompt", ""),
                negative_prompt=shot_data.get("negative_prompt", ""),
                duration_frames=int(shot_data.get("duration_frames", 81)),
                width=640,
                height=640,
                seed=None,
                character_ids=shot_data.get("characters", []),
            )
            db.add(shot)
            total_shots += 1

        created_scenes.append({
            "id": str(scene.id),
            "title": scene.title,
            "description": scene.description,
            "shot_count": len(shots_data),
        })

    # Update project
    project.total_shots = total_shots
    db.add(project)
    db.commit()

    log.info(
        "script_analysis_complete",
        project_id=str(project_id),
        scene_count=len(created_scenes),
        shot_count=total_shots,
    )

    return {
        "scenes": created_scenes,
        "total_shots": total_shots,
    }
