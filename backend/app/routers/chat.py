import json
from fastapi import APIRouter
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.graph import hcp_agent
from app.schemas import ChatRequest, ChatResponse
from app.database import SessionLocal
from app.models import Interaction

router = APIRouter(prefix="/api/chat", tags=["chat"])

# NOTE: for a real product, keep per-user/session message history (e.g. Redis).
# Kept as an in-memory dict here for demo purposes only.
_SESSION_HISTORY: dict[str, list] = {}


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_key = req.interaction_id or req.hcp_name or "default"
    history = _SESSION_HISTORY.get(session_key, [])


    user_text = req.message
    if req.interaction_id:
        user_text = f"[interaction_id={req.interaction_id}] {user_text}"

    history.append(HumanMessage(content=user_text))

    result = hcp_agent.invoke({"messages": history})
    messages = result["messages"]
    _SESSION_HISTORY[session_key] = messages

    last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage) and m.content), None)
    reply_text = last_ai.content if last_ai else "Done."

    tool_used = None
    interaction_out = None
    for m in reversed(messages):
        if getattr(m, "name", None) in (
            "log_interaction", "edit_interaction", "suggest_followups"
        ):
            tool_used = m.name
            try:
                data = json.loads(m.content)
                interaction_id = data.get("interaction_id")
                if interaction_id:
                    db = SessionLocal()
                    interaction = db.query(Interaction).filter(
                        Interaction.id == interaction_id
                    ).first()
                    if interaction:
                        interaction_out = {
                            "id": interaction.id,
                            "hcp_id": interaction.hcp_id,
                            "hcp_name": interaction.hcp.name,
                            "interaction_type": interaction.interaction_type,
                            "interaction_datetime": interaction.interaction_datetime,
                            "attendees": interaction.attendees,
                            "topics_discussed": interaction.topics_discussed,
                            "materials_shared": interaction.materials_shared,
                            "samples_distributed": interaction.samples_distributed,
                            "sentiment": interaction.sentiment,
                            "outcomes": interaction.outcomes,
                            "follow_up_actions": interaction.follow_up_actions,
                            "ai_suggested_followups": interaction.ai_suggested_followups,
                        }
                    db.close()
            except (json.JSONDecodeError, TypeError):
                pass
            break

    return ChatResponse(reply=reply_text, tool_used=tool_used, interaction=interaction_out)
