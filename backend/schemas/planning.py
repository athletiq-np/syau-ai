"""Pydantic schemas for script planning and scene breakdown."""
from pydantic import BaseModel, Field
from typing import List


class BeatSchema(BaseModel):
    """A story beat within a scene."""
    id: str = Field(..., description="Unique beat identifier")
    description: str = Field(..., description="What happens in this beat")


class ShotSchema(BaseModel):
    """A shot to be generated for a beat."""
    id: str = Field(..., description="Unique shot identifier")
    beat_id: str = Field(..., description="Which beat this shot covers")
    shot_type: str = Field(..., description="t2v (text-to-video) or i2v (image-to-video)")
    subject: str = Field(..., description="What/who is the focus of this shot")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "shot_1",
                "beat_id": "beat_1",
                "shot_type": "t2v",
                "subject": "Explorer entering the ruin"
            }
        }


class ScenePlanSchema(BaseModel):
    """Complete scene breakdown with beats and shots."""
    scene_summary: str = Field(..., description="One-line scene summary")
    characters: List[str] = Field(default_factory=list, description="Characters in scene")
    location: str = Field(..., description="Where the scene takes place")
    beats: List[BeatSchema] = Field(..., description="Story beats in sequence")
    shots: List[ShotSchema] = Field(..., description="Shots to generate from beats")

    class Config:
        json_schema_extra = {
            "example": {
                "scene_summary": "Explorer discovers a glowing mandala in ancient ruins",
                "characters": ["Explorer"],
                "location": "Stone ruin at night",
                "beats": [
                    {
                        "id": "beat_1",
                        "description": "Explorer enters the dark ruin"
                    }
                ],
                "shots": [
                    {
                        "id": "shot_1",
                        "beat_id": "beat_1",
                        "shot_type": "t2v",
                        "subject": "Explorer with flashlight"
                    }
                ]
            }
        }


class PromptPackageSchema(BaseModel):
    """Assembled prompt ready for Wan generation."""
    shot_id: str
    shot_type: str
    prompt: str = Field(..., description="Full cinematic prompt for Wan")
    negative_prompt: str = Field(default="", description="Things to avoid")
    duration_frames: int = Field(default=81, description="Number of frames (81 = 5s @ 16fps)")
    seed: int = Field(default=0, description="Random seed for reproducibility")
