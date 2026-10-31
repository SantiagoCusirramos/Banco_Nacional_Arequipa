from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from COREDB.database import db_session

router = APIRouter(prefix="/coredb", tags=["salud"])


@router.get("/salud")
def salud(db: Session = Depends(db_session)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"estado": "ok"}
