"""
Five LangGraph tools backing the HCP field-rep agent.

1. log_interaction        (required)
2. edit_interaction       (required)
3. search_hcp
4. get_interaction_history
5. suggest_followups

Each tool is a thin wrapper around the DB session + the Groq LLM, exposed
via the @tool decorator so the LangGraph ReAct-style agent can call them.
"""
import json
from datetime import datetime
from typing import List, Optional

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import HCP, Interaction, SentimentEnum, InteractionTypeEnum
from app.agent.llm import extraction_llm, summarizer_llm


def _get_or_create_hcp(db: Session, name: str) -> HCP:
    hcp = db.query(HCP).filter(HCP.name.ilike(name.strip())).first()
    if not hcp:
        hcp = HCP(name=name.strip())
        db.add(hcp)
        db.commit()
        db.refresh(hcp)
    return hcp


EXTRACTION_SYSTEM_PROMPT = """You are a clinical-sales data extraction engine for a
pharma CRM. Given a free-text or voice-transcribed description of a field rep's
visit to a Healthcare Professional (HCP), extract structured fields.

Return ONLY valid JSON, no prose, no markdown fences, matching this schema:
{
  "hcp_name": string,
  "interaction_type": "Meeting" | "Call" | "Email" | "Conference",
  "attendees": string[],
  "topics_discussed": string,
  "materials_shared": string[],
  "samples_distributed": string[],
  "sentiment": "positive" | "neutral" | "negative",
  "outcomes": string,
  "follow_up_actions": string
}
If a field isn't mentioned, use an empty string or empty list. Infer sentiment
from tone/wording if not stated explicitly (e.g. enthusiasm -> positive).
IMPORTANT: "attendees" means OTHER people who joined the meeting (e.g. a
colleague or nurse) - never include the HCP themselves in "attendees", since
they are already captured in "hcp_name".
"""


@tool
def log_interaction(raw_text: str, hcp_name_hint: Optional[str] = None) -> str:
    """Log a new HCP interaction from free-text (typed chat or voice-transcribed
    notes). Uses the LLM to summarize the conversation and extract structured
    entities (HCP name, topics, materials/samples, sentiment, outcomes,
    follow-ups), then persists a new Interaction row. Returns a JSON string
    with the created interaction's id and extracted fields."""
    db = SessionLocal()
    try:
        user_prompt = raw_text
        if hcp_name_hint:
            user_prompt += f"\n\n(Hint: the HCP being discussed is '{hcp_name_hint}')"

        resp = extraction_llm.invoke(
            [
                ("system", EXTRACTION_SYSTEM_PROMPT),
                ("user", user_prompt),
            ]
        )
        content = resp.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)

        hcp = _get_or_create_hcp(db, data.get("hcp_name") or hcp_name_hint or "Unknown HCP")

        itype = data.get("interaction_type", "Meeting")
        if itype not in [e.value for e in InteractionTypeEnum]:
            itype = "Meeting"
        sentiment = data.get("sentiment", "neutral")
        if sentiment not in [e.value for e in SentimentEnum]:
            sentiment = "neutral"

        def _as_list(value):
            return value if isinstance(value, list) else []

        interaction = Interaction(
            hcp_id=hcp.id,
            interaction_type=itype,
            interaction_datetime=datetime.utcnow(),
            attendees=_as_list(data.get("attendees")),
            topics_discussed=data.get("topics_discussed", "") or "",
            materials_shared=_as_list(data.get("materials_shared")),
            samples_distributed=_as_list(data.get("samples_distributed")),
            sentiment=sentiment,
            outcomes=data.get("outcomes", "") or "",
            follow_up_actions=data.get("follow_up_actions", "") or "",
            raw_source_text=raw_text,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        return json.dumps({
            "status": "logged",
            "interaction_id": interaction.id,
            "hcp_name": hcp.name,
            "extracted": data,
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


@tool
def edit_interaction(interaction_id: str, instruction: str) -> str:
    """Edit a previously logged interaction using a natural-language instruction,
    e.g. 'change sentiment to positive' or 'add that a brochure on OncoBoost
    was shared'. The LLM converts the instruction into a partial-update JSON
    which is then merged into the existing Interaction row."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"status": "error", "message": "interaction not found"})

        current_state = {
            "interaction_type": interaction.interaction_type,
            "attendees": interaction.attendees,
            "topics_discussed": interaction.topics_discussed,
            "materials_shared": interaction.materials_shared,
            "samples_distributed": interaction.samples_distributed,
            "sentiment": interaction.sentiment,
            "outcomes": interaction.outcomes,
            "follow_up_actions": interaction.follow_up_actions,
        }

        prompt = f"""Current interaction record (JSON): {json.dumps(current_state)}
Edit instruction from field rep: "{instruction}"

Return ONLY the JSON fields that should change (a partial update), same schema
as the current record. No prose, no markdown."""

        resp = extraction_llm.invoke([("user", prompt)])
        content = resp.content.strip().replace("```json", "").replace("```", "").strip()
        updates = json.loads(content)

        LIST_FIELDS = {"attendees", "materials_shared", "samples_distributed"}
        for key, value in updates.items():
            if not hasattr(interaction, key) or value in (None, ""):
                continue
            if key in LIST_FIELDS and not isinstance(value, list):
                continue  # skip malformed non-list values for list fields
            setattr(interaction, key, value)

        interaction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(interaction)

        return json.dumps({
            "status": "updated",
            "interaction_id": interaction.id,
            "updates": updates,
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


@tool
def search_hcp(query: str) -> str:
    """Search for existing HCPs by (partial) name. Returns each match's full
    profile: name, hospital, products/materials discussed across all visits,
    last visit date, total interaction count, and whether a follow-up is
    still pending - used for the 'HCP Name' autocomplete and for rep lookups
    like 'find Dr. X' or 'show me details on Dr. X'."""
    db = SessionLocal()
    try:
        matches = db.query(HCP).filter(HCP.name.ilike(f"%{query}%")).limit(10).all()
        results = []
        for h in matches:
            interactions = (
                db.query(Interaction)
                .filter(Interaction.hcp_id == h.id)
                .order_by(Interaction.interaction_datetime.desc())
                .all()
            )
            products = set()
            for i in interactions:
                products.update(i.materials_shared or [])
                products.update(i.samples_distributed or [])
            last_visit = interactions[0].interaction_datetime.isoformat() if interactions else None
            follow_up_pending = bool(interactions and interactions[0].follow_up_actions)
            results.append({
                "id": h.id,
                "name": h.name,
                "specialty": h.specialty,
                "hospital": h.hospital,
                "products_discussed": sorted(products),
                "last_visit": last_visit,
                "total_interactions": len(interactions),
                "follow_up_status": "pending" if follow_up_pending else "none",
            })
        return json.dumps(results)
    finally:
        db.close()


@tool
def get_interaction_history(hcp_name: str) -> str:
    """Fetch prior logged interactions for a given HCP, most recent first,
    with a per-visit summary and products discussed. Used to give the
    agent/chat context (e.g. 'last time Dr. Smith asked about pricing')
    before logging a new interaction or suggesting follow-ups."""
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.name.ilike(hcp_name.strip())).first()
        if not hcp:
            return json.dumps({"status": "not_found", "history": []})
        interactions = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == hcp.id)
            .order_by(Interaction.interaction_datetime.desc())
            .limit(5)
            .all()
        )
        return json.dumps({
            "status": "ok",
            "history": [
                {
                    "id": i.id,
                    "date": i.interaction_datetime.isoformat(),
                    "type": i.interaction_type,
                    "summary": f"{i.topics_discussed or 'No topics recorded'} - {i.outcomes or 'no outcome recorded'}",
                    "products_discussed": (i.materials_shared or []) + (i.samples_distributed or []),
                    "sentiment": i.sentiment,
                }
                for i in interactions
            ],
        })
    finally:
        db.close()


@tool
def suggest_followups(interaction_id: str) -> str:
    """Given a logged interaction, ask the LLM to propose 2-4 concrete
    follow-up actions for the field rep (e.g. 'schedule follow-up meeting in
    2 weeks', 'send Phase III PDF'), and persist them onto the interaction's
    ai_suggested_followups field."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"status": "error", "message": "interaction not found"})

        prompt = f"""Interaction summary:
Topics discussed: {interaction.topics_discussed}
Outcomes: {interaction.outcomes}
Sentiment: {interaction.sentiment}
Materials shared: {interaction.materials_shared}

Suggest 2-4 short, concrete next-step follow-up actions for the pharma field
rep (e.g. scheduling, sending materials, internal escalation). Return ONLY a
JSON array of strings."""

        resp = summarizer_llm.invoke([("user", prompt)])
        content = resp.content.strip().replace("```json", "").replace("```", "").strip()
        suggestions = json.loads(content)

        interaction.ai_suggested_followups = suggestions
        db.commit()

        return json.dumps({
            "status": "ok",
            "interaction_id": interaction.id,
            "suggestions": suggestions,
        })
    except Exception as e:
        db.rollback()
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    search_hcp,
    get_interaction_history,
    suggest_followups,
]