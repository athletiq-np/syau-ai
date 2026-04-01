from core.database import get_db
from sqlalchemy.orm import Session
from typing import Generator
from fastapi import Depends


def get_session() -> Generator[Session, None, None]:
    yield from get_db()
