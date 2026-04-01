from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict

from api.deps import get_session
from services.job_service import get_enabled_models
from schemas.job import ModelResponse

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
def list_models(db: Session = Depends(get_session)):
    models = get_enabled_models(db)
    grouped: dict[str, list] = defaultdict(list)
    for m in models:
        grouped[m.type].append(ModelResponse.model_validate(m))
    return {"models": grouped}
