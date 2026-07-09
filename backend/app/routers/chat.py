import json
from fastapi import APIRouter
from langchain_core.messages import HumanMessage, AIMessage

from app.schemas import ChatRequest, ChatResponse
from app.agent.graph import hcp_agent_graph
from app.database import SessionLocal
from app.models import Interaction, HCP

router = APIRouter(prefix="/api/chat", tags=["chat"])

_SESSIONS: dict[str, list] = {}


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest):
    history = _SESSIONS.get(req.session_id, [])
    history.append(HumanMessage(content=req.message))

    result = hcp_agent_graph.invoke({"messages": history})
    messages = result["messages"]
    _SESSIONS[req.session_id] = messages

    tool_calls_used = []
    logged_interaction_id = None
    suggestions = []

    for m in messages:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                tool_calls_used.append(tc["name"])
        if getattr(m, "name", None) == "log_interaction":
            try:
                payload = json.loads(m.content)
                logged_interaction_id = payload.get("interaction_id")
            except Exception:
                pass
        if getattr(m, "name", None) == "suggest_follow_ups":
            try:
                payload = json.loads(m.content)
                suggestions = payload.get("suggestions", [])
            except Exception:
                pass

    final_reply = messages[-1].content if messages else ""

    interaction_out = None
    if logged_interaction_id:
        db = SessionLocal()
        try:
            row = db.query(Interaction).filter(Interaction.id == logged_interaction_id).first()
            if row:
                hcp = db.query(HCP).filter(HCP.id == row.hcp_id).first()
                interaction_out = {
                    "id": row.id, "hcp_id": row.hcp_id, "hcp_name": hcp.name if hcp else None,
                    "interaction_type": row.interaction_type, "date": row.date, "time": row.time,
                    "attendees": row.attendees, "topics_discussed": row.topics_discussed,
                    "sentiment": row.sentiment, "outcomes": row.outcomes,
                    "follow_up_actions": row.follow_up_actions, "source": row.source,
                }
        finally:
            db.close()

    return ChatResponse(
        reply=final_reply,
        tool_calls=tool_calls_used,
        interaction=interaction_out,
        suggested_follow_ups=suggestions,
    )
