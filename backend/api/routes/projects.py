from __future__ import annotations
import structlog
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from api.deps import get_db
from schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectDetailResponse, ProjectListResponse,
    CharacterCreate, CharacterResponse, ShotResponse, SceneResponse,
    ScriptAnalysisResponse
)
from models.project import Project, Character, Scene, Shot, ProjectStatus, ShotStatus, ShotType
from models.job import AIModel
from storage.minio import get_presigned_url

log = structlog.get_logger()

router = APIRouter(prefix="/projects", tags=["projects"])


def _build_project_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        status=project.status,
        total_shots=project.total_shots,
        output_url=get_presigned_url(project.output_key) if project.output_key else None,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _build_shot_response(shot: Shot) -> ShotResponse:
    return ShotResponse(
        id=shot.id,
        scene_id=shot.scene_id,
        project_id=shot.project_id,
        order_index=shot.order_index,
        shot_type=shot.shot_type,
        status=shot.status,
        prompt=shot.prompt,
        negative_prompt=shot.negative_prompt,
        duration_frames=shot.duration_frames,
        width=shot.width,
        height=shot.height,
        seed=shot.seed,
        character_ids=shot.character_ids,
        output_url=get_presigned_url(shot.output_key) if shot.output_key else None,
        created_at=shot.created_at,
        completed_at=shot.completed_at,
        error=shot.error,
    )


# ============================================================================
# PROJECT CRUD
# ============================================================================

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Create a new project"""
    project = Project(
        title=req.title,
        description=req.description,
        script=req.script,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    log.info("project_created", project_id=str(project.id))
    return _build_project_response(project)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    """List all projects (paginated)"""
    query = db.query(Project).order_by(Project.created_at.desc())
    total = query.count()
    items = query.offset(skip).limit(limit).all()

    projects = [_build_project_response(p) for p in items]
    return ProjectListResponse(
        items=projects,
        total=total,
        page=skip // limit,
        page_size=limit,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> ProjectDetailResponse:
    """Get project with full details (characters, scenes, shots)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    characters = db.query(Character).filter(Character.project_id == project_id).all()
    scenes = db.query(Scene).filter(Scene.project_id == project_id).order_by(Scene.order_index).all()

    scene_responses = []
    for scene in scenes:
        shots = db.query(Shot).filter(Shot.scene_id == scene.id).order_by(Shot.order_index).all()
        shot_responses = [_build_shot_response(s) for s in shots]
        scene_data = SceneResponse.model_validate(scene).model_dump()
        scene_data["shots"] = shot_responses
        scene_responses.append(scene_data)

    return ProjectDetailResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        status=project.status,
        script=project.script,
        total_shots=project.total_shots,
        output_url=get_presigned_url(project.output_key) if project.output_key else None,
        characters=[CharacterResponse.model_validate(c) for c in characters],
        scenes=scene_responses,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    req: ProjectUpdate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Update project fields (all optional)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if req.title is not None:
        project.title = req.title
    if req.description is not None:
        project.description = req.description
    if req.script is not None:
        project.script = req.script
    project.updated_at = datetime.now(timezone.utc)

    db.add(project)
    db.commit()
    db.refresh(project)
    log.info("project_updated", project_id=str(project_id))
    return _build_project_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a project and all related data"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    db.delete(project)
    db.commit()
    log.info("project_deleted", project_id=str(project_id))


# ============================================================================
# CHARACTER MANAGEMENT
# ============================================================================

@router.post("/{project_id}/characters", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
def create_character(
    project_id: UUID,
    req: CharacterCreate,
    db: Session = Depends(get_db),
) -> CharacterResponse:
    """Add a character to a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    character = Character(
        project_id=project_id,
        name=req.name,
        description=req.description,
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    log.info("character_created", project_id=str(project_id), character_id=str(character.id))
    return CharacterResponse.model_validate(character)


@router.get("/{project_id}/characters", response_model=list[CharacterResponse])
def list_characters(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> list[CharacterResponse]:
    """List characters in a project"""
    characters = db.query(Character).filter(Character.project_id == project_id).all()
    return [CharacterResponse.model_validate(c) for c in characters]


@router.delete("/{project_id}/characters/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character(
    project_id: UUID,
    character_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a character"""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.project_id == project_id
    ).first()
    if not character:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    db.delete(character)
    db.commit()
    log.info("character_deleted", character_id=str(character_id))


# ============================================================================
# SHOT MANAGEMENT
# ============================================================================

@router.patch("/{project_id}/shots/{shot_id}", response_model=ShotResponse)
def update_shot(
    project_id: UUID,
    shot_id: UUID,
    prompt: str = None,
    negative_prompt: str = None,
    db: Session = Depends(get_db),
) -> ShotResponse:
    """Edit shot prompt before generation"""
    shot = db.query(Shot).filter(
        Shot.id == shot_id,
        Shot.project_id == project_id
    ).first()
    if not shot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shot not found")

    if shot.status != ShotStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only edit pending shots")

    if prompt is not None:
        shot.prompt = prompt
    if negative_prompt is not None:
        shot.negative_prompt = negative_prompt

    db.add(shot)
    db.commit()
    db.refresh(shot)
    return _build_shot_response(shot)


@router.delete("/{project_id}/shots/{shot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shot(
    project_id: UUID,
    shot_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a shot"""
    shot = db.query(Shot).filter(
        Shot.id == shot_id,
        Shot.project_id == project_id
    ).first()
    if not shot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shot not found")

    db.delete(shot)
    db.commit()
    log.info("shot_deleted", shot_id=str(shot_id), project_id=str(project_id))


# ============================================================================
# SCENE MANAGEMENT
# ============================================================================

@router.post("/{project_id}/scenes/{scene_id}/reference-image", status_code=status.HTTP_200_OK)
def upload_scene_reference(
    project_id: UUID,
    scene_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload reference image for a scene"""
    scene = db.query(Scene).filter(
        Scene.id == scene_id,
        Scene.project_id == project_id
    ).first()
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")

    log.info("scene_reference_image_uploaded", scene_id=str(scene_id), filename=file.filename)
    return {"status": "uploaded", "filename": file.filename}


# ============================================================================
# SCRIPT ANALYSIS
# ============================================================================

@router.post("/{project_id}/script", response_model=ScriptAnalysisResponse)
def analyze_script(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> ScriptAnalysisResponse:
    """
    Analyze project script and create scenes/shots using Qwen.
    Existing scenes and shots are NOT deleted; new ones are appended.
    """
    from services.script_analyzer import analyze_script as analyze_script_service

    try:
        result = analyze_script_service(project_id, db)

        # Return the updated project with all scenes and shots
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        scenes = db.query(Scene).filter(Scene.project_id == project_id).order_by(Scene.order_index).all()
        scenes_response = []
        for scene in scenes:
            shots = db.query(Shot).filter(Shot.scene_id == scene.id).order_by(Shot.order_index).all()
            shot_responses = [_build_shot_response(s) for s in shots]
            scenes_response.append({
                "id": str(scene.id),
                "title": scene.title,
                "description": scene.description,
                "shots": shot_responses,
            })

        log.info("script_analysis_api_complete", project_id=str(project_id), scene_count=len(scenes_response))
        return ScriptAnalysisResponse(scenes=scenes_response)

    except ValueError as e:
        log.error("script_analysis_validation_failed", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        log.error("script_analysis_failed", project_id=str(project_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Script analysis failed")


# ============================================================================
# GENERATION
# ============================================================================

@router.post("/{project_id}/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_project(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """
    Start generating all shots in the project.

    Enqueues individual shot tasks and schedules final stitching.
    Returns immediately with project status.
    """
    from workers.studio_worker import run_shot_job, stitch_project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.status != ProjectStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project status is {project.status}, must be draft"
        )

    # Get all pending shots
    shots = db.query(Shot).filter(
        Shot.project_id == project_id,
        Shot.status == ShotStatus.pending,
    ).order_by(Shot.order_index).all()

    if not shots:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No shots to generate")

    # Enqueue all shot tasks with a group/chain
    from celery import chain, group

    # Create a chain: shot1 -> shot2 -> shot3 -> stitch
    shot_tasks = [
        run_shot_job.s(str(shot.id))
        for shot in shots
    ]
    stitch_task = stitch_project.si(str(project_id))  # Use .si() for immutable (ignores previous output)

    # Execute shot tasks one by one, then stitch
    workflow = chain(*shot_tasks, stitch_task)
    workflow.apply_async()

    # Update project status
    project.status = ProjectStatus.processing
    db.add(project)
    db.commit()

    log.info(
        "project_generation_started",
        project_id=str(project_id),
        shot_count=len(shots),
    )

    return {
        "status": "accepted",
        "project_id": str(project_id),
        "shot_count": len(shots),
        "message": "Generation started"
    }
