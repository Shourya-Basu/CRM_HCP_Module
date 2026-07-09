from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HCP

router = APIRouter(prefix="/api/hcps", tags=["hcps"])


@router.get("")
def search_hcps(q: str = "", db: Session = Depends(get_db)):
    query = db.query(HCP)
    if q:
        query = query.filter(HCP.name.ilike(f"%{q}%"))
    rows = query.limit(20).all()
    return [{"id": h.id, "name": h.name, "specialty": h.specialty, "institution": h.institution} for h in rows]
