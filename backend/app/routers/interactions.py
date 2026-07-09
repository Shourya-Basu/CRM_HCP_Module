from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HCP, Interaction, InteractionMaterial, InteractionSample
from app.schemas import InteractionCreate, InteractionUpdate, InteractionOut

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("", response_model=InteractionOut)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    hcp = db.query(HCP).filter(HCP.name.ilike(payload.hcp_name.strip())).first()
    if not hcp:
        hcp = HCP(name=payload.hcp_name.strip())
        db.add(hcp)
        db.commit()
        db.refresh(hcp)

    interaction = Interaction(
        hcp_id=hcp.id,
        interaction_type=payload.interaction_type,
        date=payload.date,
        time=payload.time,
        attendees=payload.attendees,
        topics_discussed=payload.topics_discussed,
        sentiment=payload.sentiment,
        outcomes=payload.outcomes,
        follow_up_actions=payload.follow_up_actions,
        source=payload.source,
        raw_transcript=payload.raw_transcript,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    for m in payload.materials or []:
        db.add(InteractionMaterial(interaction_id=interaction.id, material_name=m.material_name))
    for s in payload.samples or []:
        db.add(InteractionSample(interaction_id=interaction.id, sample_name=s.sample_name,
                                  quantity=s.quantity, lot_number=s.lot_number))
    db.commit()

    return InteractionOut(
        id=interaction.id, hcp_id=hcp.id, hcp_name=hcp.name,
        interaction_type=interaction.interaction_type, date=interaction.date, time=interaction.time,
        attendees=interaction.attendees, topics_discussed=interaction.topics_discussed,
        sentiment=interaction.sentiment, outcomes=interaction.outcomes,
        follow_up_actions=interaction.follow_up_actions, source=interaction.source,
    )


@router.get("", response_model=list[InteractionOut])
def list_interactions(hcp_name: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Interaction)
    if hcp_name:
        hcp = db.query(HCP).filter(HCP.name.ilike(hcp_name)).first()
        if not hcp:
            return []
        q = q.filter(Interaction.hcp_id == hcp.id)
    rows = q.order_by(Interaction.created_at.desc()).all()
    out = []
    for r in rows:
        hcp = db.query(HCP).filter(HCP.id == r.hcp_id).first()
        out.append(InteractionOut(
            id=r.id, hcp_id=r.hcp_id, hcp_name=hcp.name if hcp else None,
            interaction_type=r.interaction_type, date=r.date, time=r.time,
            attendees=r.attendees, topics_discussed=r.topics_discussed,
            sentiment=r.sentiment, outcomes=r.outcomes,
            follow_up_actions=r.follow_up_actions, source=r.source,
        ))
    return out


@router.patch("/{interaction_id}", response_model=InteractionOut)
def update_interaction(interaction_id: str, payload: InteractionUpdate, db: Session = Depends(get_db)):
    row = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    hcp = db.query(HCP).filter(HCP.id == row.hcp_id).first()
    return InteractionOut(
        id=row.id, hcp_id=row.hcp_id, hcp_name=hcp.name if hcp else None,
        interaction_type=row.interaction_type, date=row.date, time=row.time,
        attendees=row.attendees, topics_discussed=row.topics_discussed,
        sentiment=row.sentiment, outcomes=row.outcomes,
        follow_up_actions=row.follow_up_actions, source=row.source,
    )


@router.delete("/{interaction_id}")
def delete_interaction(interaction_id: str, db: Session = Depends(get_db)):
    row = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "id": interaction_id}
