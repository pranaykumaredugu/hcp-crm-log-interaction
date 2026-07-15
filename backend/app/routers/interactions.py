from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HCP, Interaction
from app.schemas import InteractionCreate, InteractionUpdate, InteractionOut, HCPOut

router = APIRouter(prefix="/api/interactions", tags=["interactions"])
hcp_router = APIRouter(prefix="/api/hcps", tags=["hcps"])


@hcp_router.get("", response_model=list[HCPOut])
def list_hcps(q: str = "", db: Session = Depends(get_db)):
    query = db.query(HCP)
    if q:
        query = query.filter(HCP.name.ilike(f"%{q}%"))
    return query.limit(20).all()


@router.post("", response_model=InteractionOut)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    """Used by the structured form's 'Log' button (non-chat path)."""
    hcp = db.query(HCP).filter(HCP.name.ilike(payload.hcp_name.strip())).first()
    if not hcp:
        hcp = HCP(name=payload.hcp_name.strip())
        db.add(hcp)
        db.commit()
        db.refresh(hcp)

    interaction = Interaction(
        hcp_id=hcp.id,
        interaction_type=payload.interaction_type,
        attendees=payload.attendees,
        topics_discussed=payload.topics_discussed,
        materials_shared=payload.materials_shared,
        samples_distributed=payload.samples_distributed,
        sentiment=payload.sentiment,
        outcomes=payload.outcomes,
        follow_up_actions=payload.follow_up_actions,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


@router.get("/{interaction_id}", response_model=InteractionOut)
def get_interaction(interaction_id: str, db: Session = Depends(get_db)):
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(404, "Interaction not found")
    return interaction


@router.patch("/{interaction_id}", response_model=InteractionOut)
def update_interaction(interaction_id: str, payload: InteractionUpdate, db: Session = Depends(get_db)):
    """Used by the structured form's edit path (non-chat)."""
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(404, "Interaction not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(interaction, field, value)

    db.commit()
    db.refresh(interaction)
    return interaction


@router.get("", response_model=list[InteractionOut])
def list_interactions(hcp_name: str = "", db: Session = Depends(get_db)):
    query = db.query(Interaction)
    if hcp_name:
        query = query.join(HCP).filter(HCP.name.ilike(f"%{hcp_name}%"))
    return query.order_by(Interaction.interaction_datetime.desc()).limit(50).all()
