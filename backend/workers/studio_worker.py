"""Studio worker — shot generation and film stitching via Celery."""
import time
import subprocess
import base64
import structlog
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from workers.celery_app import celery_app
from workers.utils import publish_ws_event
from models.project import Shot, Project, ShotStatus, ShotType
from inference.comfyui_client import ComfyUIClient
from storage.minio import upload_bytes, download_bytes, get_presigned_url

log = structlog.get_logger()


def _publish_project_event(project_id: str, **kwargs):
    """Publish event to project WebSocket channel"""
    channel = f"project_events:{project_id}"
    from core.redis import get_redis
    import json
    redis = get_redis()
    redis.publish(channel, json.dumps(kwargs))


@celery_app.task(name="workers.studio_worker.run_shot_job", bind=True, max_retries=2)
def run_shot_job(self, shot_id: str) -> dict:
    """Generate a single shot video."""
    log.info("shot_job_received", shot_id=shot_id)
    db = SessionLocal()
    try:
        shot = db.query(Shot).filter(Shot.id == UUID(shot_id)).first()
        if not shot:
            raise ValueError(f"Shot {shot_id} not found")

        project = db.query(Project).filter(Project.id == shot.project_id).first()
        if not project:
            raise ValueError(f"Project {shot.project_id} not found")

        # Update shot status
        shot.status = ShotStatus.running
        db.add(shot)
        db.commit()

        log.info(
            "shot_processing_started",
            shot_id=shot_id,
            project_id=str(shot.project_id),
            shot_type=shot.shot_type,
        )
        _publish_project_event(
            str(shot.project_id),
            type="shot_start",
            shot_id=shot_id,
            status="running",
        )

        # Setup ComfyUI client
        comfyui_url = settings.comfyui_url or "http://host.docker.internal:8188"
        comfyui = ComfyUIClient(base_url=comfyui_url)
        start = time.time()

        # Handle I2V vs T2V
        if shot.shot_type == ShotType.i2v and shot.reference_key:
            # I2V mode: download reference image, upload to ComfyUI
            log.info("shot_i2v_downloading_reference", shot_id=shot_id, ref_key=shot.reference_key)
            try:
                image_bytes = download_bytes(shot.reference_key)
                image_filename = comfyui.upload_image(image_bytes, filename=f"ref_{shot_id}.jpg")
                log.info("shot_i2v_reference_uploaded", shot_id=shot_id, filename=image_filename)
            except Exception as e:
                log.warning(
                    "shot_i2v_reference_failed_fallback_to_t2v",
                    shot_id=shot_id,
                    error=str(e),
                )
                image_filename = None

            if image_filename:
                result = comfyui.infer_wan_i2v(
                    image_filename=image_filename,
                    prompt=shot.prompt,
                    negative_prompt=shot.negative_prompt,
                    num_frames=shot.duration_frames,
                    height=shot.height,
                    width=shot.width,
                    seed=shot.seed or 0,
                    on_progress=lambda pct, msg: _publish_project_event(
                        str(shot.project_id),
                        type="shot_progress",
                        shot_id=shot_id,
                        progress=pct,
                        message=msg,
                    ),
                )
            else:
                # Fallback to T2V if reference fails
                result = comfyui.infer_wan_t2v(
                    prompt=shot.prompt,
                    negative_prompt=shot.negative_prompt,
                    num_frames=shot.duration_frames,
                    height=shot.height,
                    width=shot.width,
                    seed=shot.seed or 0,
                    on_progress=lambda pct, msg: _publish_project_event(
                        str(shot.project_id),
                        type="shot_progress",
                        shot_id=shot_id,
                        progress=pct,
                        message=msg,
                    ),
                )
        else:
            # T2V mode: text-to-video only
            result = comfyui.infer_wan_t2v(
                prompt=shot.prompt,
                negative_prompt=shot.negative_prompt,
                num_frames=shot.duration_frames,
                height=shot.height,
                width=shot.width,
                seed=shot.seed or 0,
                on_progress=lambda pct, msg: _publish_project_event(
                    str(shot.project_id),
                    type="shot_progress",
                    shot_id=shot_id,
                    progress=pct,
                    message=msg,
                ),
            )

        # Upload result to MinIO
        ext = result["filename"].rsplit(".", 1)[-1] if "." in result["filename"] else "mp4"
        output_key = f"projects/{shot.project_id}/shots/{shot_id}.{ext}"
        upload_bytes(output_key, result["video_bytes"], content_type=result["content_type"])

        # Extract last frame for I2V continuity
        # (Will be used by next shot as reference)
        try:
            last_frame_bytes = extract_last_frame(result["video_bytes"])
            last_frame_key = f"projects/{shot.project_id}/shots/{shot_id}_last_frame.jpg"
            upload_bytes(last_frame_key, last_frame_bytes, content_type="image/jpeg")
            log.info("shot_last_frame_extracted", shot_id=shot_id, key=last_frame_key)

            # Set this frame as reference for next shot with same character
            if shot.character_ids:
                set_character_references(db, shot.project_id, shot.order_index, last_frame_key)
        except Exception as e:
            log.warning("shot_last_frame_extraction_failed", shot_id=shot_id, error=str(e))

        # Update shot record
        duration = time.time() - start
        shot.status = ShotStatus.done
        shot.output_key = output_key
        shot.completed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.add(shot)
        db.commit()

        log.info(
            "shot_completed",
            shot_id=shot_id,
            duration_seconds=round(duration, 2),
            output_key=output_key,
        )
        _publish_project_event(
            str(shot.project_id),
            type="shot_complete",
            shot_id=shot_id,
            output_key=output_key,
            duration_seconds=round(duration, 2),
        )

        return {"status": "done", "shot_id": shot_id, "output_key": output_key}

    except Exception as exc:
        log.error("shot_failed", shot_id=shot_id, error=str(exc))
        shot = db.query(Shot).filter(Shot.id == UUID(shot_id)).first()
        if shot:
            shot.status = ShotStatus.failed
            shot.error = str(exc)
            db.add(shot)
            db.commit()

        _publish_project_event(
            str(shot.project_id) if shot else "unknown",
            type="shot_failed",
            shot_id=shot_id,
            error=str(exc),
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10)
        raise

    finally:
        db.close()


@celery_app.task(name="workers.studio_worker.stitch_project", bind=True, max_retries=1)
def stitch_project(self, project_id: str) -> dict:
    """Stitch all completed shots into final film."""
    log.info("stitch_project_started", project_id=project_id)
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == UUID(project_id)).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        _publish_project_event(
            project_id,
            type="stitch_start",
            status="stitching",
            message="Downloading shots...",
        )

        # Fetch all shots in order
        shots = db.query(Shot).filter(Shot.project_id == UUID(project_id)).order_by(Shot.order_index).all()
        completed_shots = [s for s in shots if s.status == ShotStatus.done and s.output_key]

        if not completed_shots:
            raise ValueError("No completed shots to stitch")

        log.info(
            "stitch_downloading_shots",
            project_id=project_id,
            shot_count=len(completed_shots),
        )

        # Download all shots to temp directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            shot_files = []

            for i, shot in enumerate(completed_shots):
                shot_filename = tmpdir_path / f"shot_{i:03d}.mp4"
                shot_bytes = download_bytes(shot.output_key)
                shot_filename.write_bytes(shot_bytes)
                shot_files.append(shot_filename)
                log.info("shot_downloaded", shot_id=str(shot.id), file=str(shot_filename))

            _publish_project_event(
                project_id,
                type="stitch_progress",
                message="Running FFmpeg...",
            )

            # Create FFmpeg concat file
            concat_file = tmpdir_path / "concat.txt"
            concat_content = "\n".join([f"file '{f}'" for f in shot_files])
            concat_file.write_text(concat_content)

            # Run FFmpeg
            output_file = tmpdir_path / "final.mp4"
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",  # Copy without re-encoding for speed
                "-y",  # Overwrite output file
                str(output_file),
            ]

            log.info("ffmpeg_starting", command=" ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                log.error("ffmpeg_failed", stdout=result.stdout, stderr=result.stderr)
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")

            log.info("ffmpeg_completed", file=str(output_file), size_bytes=output_file.stat().st_size)

            # Upload final film to MinIO
            _publish_project_event(
                project_id,
                type="stitch_progress",
                message="Uploading final film...",
            )

            final_bytes = output_file.read_bytes()
            final_key = f"projects/{project_id}/final.mp4"
            upload_bytes(final_key, final_bytes, content_type="video/mp4")

            # Update project
            project.output_key = final_key
            project.status = __import__("models.project", fromlist=["ProjectStatus"]).ProjectStatus.done
            db.add(project)
            db.commit()

            log.info(
                "stitch_complete",
                project_id=project_id,
                output_key=final_key,
                size_bytes=len(final_bytes),
            )

            _publish_project_event(
                project_id,
                type="stitch_complete",
                status="done",
                output_key=final_key,
                message="Film complete!",
            )

            return {"status": "done", "project_id": project_id, "output_key": final_key}

    except Exception as exc:
        log.error("stitch_failed", project_id=project_id, error=str(exc))

        project = db.query(Project).filter(Project.id == UUID(project_id)).first()
        if project:
            project.status = __import__("models.project", fromlist=["ProjectStatus"]).ProjectStatus.failed
            db.add(project)
            db.commit()

        _publish_project_event(
            project_id,
            type="stitch_failed",
            status="failed",
            error=str(exc),
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        raise

    finally:
        db.close()


def extract_last_frame(video_bytes: bytes) -> bytes:
    """Extract last frame from video bytes using FFmpeg."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        video_file = tmpdir_path / "video.mp4"
        frame_file = tmpdir_path / "frame.jpg"

        video_file.write_bytes(video_bytes)

        cmd = [
            "ffmpeg",
            "-sseof", "-0.1",  # Seek 0.1s from end
            "-i", str(video_file),
            "-frames:v", "1",
            "-y",
            str(frame_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg frame extraction failed: {result.stderr}")

        return frame_file.read_bytes()


def set_character_references(db: Session, project_id: UUID, current_shot_index: int, reference_key: str):
    """
    Set extracted frame as reference for subsequent shots with same character.

    When a shot with character X completes, use its last frame as the I2V
    reference for the next shot with character X.
    """
    from models.project import Character, Shot as ShotModel

    try:
        current_shot = db.query(ShotModel).filter(
            ShotModel.project_id == project_id,
            ShotModel.order_index == current_shot_index,
        ).first()

        if not current_shot or not current_shot.character_ids:
            return

        # Find next shots with same character
        next_shots = db.query(ShotModel).filter(
            ShotModel.project_id == project_id,
            ShotModel.order_index > current_shot_index,
        ).order_by(ShotModel.order_index).all()

        for next_shot in next_shots:
            # Check if shot has any of the same characters
            if any(char_id in next_shot.character_ids for char_id in current_shot.character_ids):
                # Set reference if not already set
                if not next_shot.reference_key:
                    next_shot.reference_key = reference_key
                    next_shot.shot_type = ShotType.i2v
                    db.add(next_shot)
                    log.info(
                        "character_reference_auto_set",
                        from_shot=str(current_shot.id),
                        to_shot=str(next_shot.id),
                        reference_key=reference_key,
                    )

        db.commit()
    except Exception as e:
        log.warning("set_character_references_failed", error=str(e))
