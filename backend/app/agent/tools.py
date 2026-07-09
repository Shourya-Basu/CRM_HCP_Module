"""
Tools available to the LangGraph HCP-CRM agent.

Two tools are mandated by the assignment: `log_interaction` and `edit_interaction`.
Three more sales-relevant tools are added so the agent can look up context and
proactively help a field rep instead of only writing records.
"""
import json
import datetime as dt
from typing import Optional, List

from langchain_core.tools import tool

from app.database import SessionLocal
from app.models import HCP, Interaction, InteractionMaterial, InteractionSample, Material, Sample
from app.agent.llm import context_llm

MAX_DATE_DRIFT_DAYS = 365


def _sanitize_date(date_str: Optional[str]) -> str:
    """
    Ensure the date stored in the database is reasonable.

    Rules:
    - Missing date -> today
    - Invalid format -> today
    - More than 365 days away from today -> today
    """

    today = dt.date.today()

    if not date_str:
        return today.isoformat()

    try:
        parsed = dt.date.fromisoformat(date_str)
    except ValueError:
        return today.isoformat()

    if abs((parsed - today).days) > MAX_DATE_DRIFT_DAYS:
        return today.isoformat()

    return parsed.isoformat()


def _get_or_create_hcp(db, hcp_name: str) -> HCP:
    hcp = db.query(HCP).filter(HCP.name.ilike(hcp_name.strip())).first()
    if not hcp:
        hcp = HCP(name=hcp_name.strip())
        db.add(hcp)
        db.commit()
        db.refresh(hcp)
    return hcp


@tool
def log_interaction(
    hcp_name: str,
    interaction_type: str = "Meeting",
    date: Optional[str] = None,
    attendees: Optional[str] = None,
    topics_discussed: Optional[str] = None,
    sentiment: Optional[str] = "Neutral",
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
    materials_shared: Optional[str] = None,
    samples_distributed: Optional[str] = None,
    raw_text: Optional[str] = None,
) -> str:
    """Log a new HCP interaction. Use this whenever a rep describes a meeting,
    call, or email with a healthcare professional in free text (e.g. via chat
    or a dictated voice note). Extract structured fields yourself before
    calling this tool: hcp_name (required), interaction_type
    (Meeting/Call/Email/Conference), date (YYYY-MM-DD if mentioned, else
    today), attendees (comma separated), topics_discussed (short summary),
    sentiment (Positive/Neutral/Negative inferred from tone), outcomes,
    follow_up_actions, materials_shared (comma separated names) and
    samples_distributed (comma separated names). Pass the original
    unedited text in raw_text for auditability.
    """
    db = SessionLocal()

    try:
        hcp = _get_or_create_hcp(db, hcp_name)
        interaction = Interaction(
            hcp_id=hcp.id,
            interaction_type=interaction_type,
            date=_sanitize_date(date),
            time=dt.datetime.now().strftime("%H:%M"),
            attendees=attendees,
            topics_discussed=topics_discussed,
            sentiment=sentiment or "Neutral",
            outcomes=outcomes,
            follow_up_actions=follow_up_actions,
            source="chat",
            raw_transcript=raw_text,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        for m in [x.strip() for x in (materials_shared or "").split(",") if x.strip()]:
            db.add(InteractionMaterial(interaction_id=interaction.id, material_name=m))
        for s in [x.strip() for x in (samples_distributed or "").split(",") if x.strip()]:
            db.add(InteractionSample(interaction_id=interaction.id, sample_name=s, quantity=1))
        db.commit()

        return json.dumps({
            "status": "logged",
            "interaction_id": interaction.id,
            "hcp_name": hcp.name,
            "date": interaction.date,
            "sentiment": interaction.sentiment,
        })
    finally:
        db.close()

@tool
def edit_interaction(
    field: str,
    new_value: str,
    interaction_id: Optional[str] = None,
    hcp_name: Optional[str] = None,
) -> str:
    """Edit a single field of a previously logged interaction. Use this when
    the rep says something like "actually change the sentiment to positive"
    or "add that we also discussed pricing".

    Prefer passing `interaction_id` if you already know it (e.g. it was just
    returned by log_interaction in this conversation). If you do NOT know the
    exact interaction_id — for example the rep refers to an HCP by name only,
    like "change Dr. Sharma's last visit to negative" — pass `hcp_name`
    instead and this tool will resolve it to that HCP's most recently logged
    interaction. NEVER invent or guess an interaction_id.

    `field` must be one of: interaction_type, date, time, attendees,
    topics_discussed, sentiment, outcomes, follow_up_actions.
    `new_value` is the replacement text (for topics_discussed/outcomes/
    follow_up_actions you may append rather than fully overwrite, based on
    the rep's intent).
    """
    allowed_fields = {
        "interaction_type", "date", "time", "attendees",
        "topics_discussed", "sentiment", "outcomes", "follow_up_actions",
    }
    if field not in allowed_fields:
        return json.dumps({"status": "error", "message": f"Field '{field}' is not editable."})

    # Guard against the LLM writing an invalid value into a controlled field.
    if field == "sentiment" and new_value not in {"Positive", "Neutral", "Negative"}:
        return json.dumps({
            "status": "error",
            "message": f"'{new_value}' is not a valid sentiment. Must be Positive, Neutral, or Negative.",
        })
    if field == "interaction_type" and new_value not in {"Meeting", "Call", "Email", "Conference"}:
        return json.dumps({
            "status": "error",
            "message": f"'{new_value}' is not a valid interaction_type. Must be Meeting, Call, Email, or Conference.",
        })

    if not interaction_id and not hcp_name:
        return json.dumps({
            "status": "error",
            "message": "Provide either interaction_id or hcp_name to identify which interaction to edit.",
        })

    db = SessionLocal()
    try:
        interaction = None
        if interaction_id:
            interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
            if not interaction:
                return json.dumps({"status": "error", "message": "Interaction not found for that interaction_id."})
        else:
            hcp = db.query(HCP).filter(HCP.name.ilike(hcp_name.strip())).first()
            if not hcp:
                return json.dumps({"status": "error", "message": f"No HCP found matching '{hcp_name}'."})
            interaction = (
                db.query(Interaction)
                .filter(Interaction.hcp_id == hcp.id)
                .order_by(Interaction.created_at.desc())
                .first()
            )
            if not interaction:
                return json.dumps({"status": "error", "message": f"No logged interactions found for {hcp.name}."})

        old_value = getattr(interaction, field)
        if field == "date":
            new_value = _sanitize_date(new_value)
        setattr(interaction, field, new_value)
        interaction.updated_at = dt.datetime.utcnow()
        db.commit()
        return json.dumps({
            "status": "updated",
            "interaction_id": interaction.id,
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
        })
    finally:
        db.close()


@tool
def search_hcp_history(hcp_name: str, limit: int = 5) -> str:
    """Look up recent past interactions for a named HCP so the agent can give
    context-aware suggestions (e.g. avoid repeating the same talking points,
    or flag that samples are overdue for renewal). Returns the most recent
    interactions first.
    """
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.name.ilike(hcp_name.strip())).first()
        if not hcp:
            return json.dumps({"status": "not_found", "hcp_name": hcp_name})
        rows = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == hcp.id)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
            .all()
        )
        history = [{
            "date": r.date,
            "type": r.interaction_type,
            "topics": r.topics_discussed,
            "sentiment": r.sentiment,
            "outcomes": r.outcomes,
        } for r in rows]
        return json.dumps({"status": "ok", "hcp_name": hcp.name, "history": history})
    finally:
        db.close()


@tool
def search_materials_and_samples(query: str) -> str:
    """Search the approved marketing materials and sample catalog by product
    or keyword, so the agent can confirm what is available to share/distribute
    before logging it (compliance requires only cataloged items are recorded).
    """
    db = SessionLocal()
    try:
        materials = db.query(Material).filter(Material.name.ilike(f"%{query}%")).all()
        samples = db.query(Sample).filter(Sample.name.ilike(f"%{query}%")).all()
        return json.dumps({
            "materials": [{"name": m.name, "product": m.product} for m in materials],
            "samples": [{"name": s.name, "lot_number": s.lot_number, "available": s.quantity_available} for s in samples],
        })
    finally:
        db.close()


@tool
def suggest_follow_ups(topics_discussed: str, sentiment: str = "Neutral", outcomes: Optional[str] = None) -> str:
    """Generate 2-4 concrete, sales-appropriate follow-up action suggestions
    for a rep based on what was discussed, the HCP's sentiment, and the
    outcomes of the interaction (e.g. schedule a follow-up meeting, send
    requested literature, add to an advisory board list). Use this after
    logging an interaction, or whenever the rep explicitly asks "what should
    I do next".
    """
    prompt = (
        "You are a pharma sales-ops assistant. Based on the interaction details "
        "below, propose 2-4 short, concrete next-step actions for the field rep. "
        "Return ONLY a JSON array of short strings, no prose.\n\n"
        f"Topics discussed: {topics_discussed}\n"
        f"HCP sentiment: {sentiment}\n"
        f"Outcomes: {outcomes or 'N/A'}\n"
    )
    resp = context_llm.invoke(prompt)
    text = resp.content.strip()
    try:
        # tolerate the model wrapping in code fences
        text = text.replace("```json", "").replace("```", "").strip()
        suggestions = json.loads(text)
        if not isinstance(suggestions, list):
            raise ValueError
    except Exception:
        suggestions = [line.strip("-* ") for line in text.splitlines() if line.strip()][:4]
    return json.dumps({"suggestions": suggestions})


@tool
def summarize_voice_note(transcript: str) -> str:
    """Summarize a raw dictated voice-note transcript into a concise
    topics_discussed string suitable for the CRM record. Requires the rep to
    have given consent to record/transcribe (consent is captured in the UI
    before this tool is ever invoked). Use this before log_interaction when
    the rep provides a long, unstructured transcript rather than clean notes.
    """
    prompt = (
        "Summarize this field rep's dictated voice note into 2-3 concise "
        "bullet-style sentences capturing topics discussed, any commitments "
        "made, and the HCP's reaction. Do not invent details.\n\n"
        f"Transcript:\n{transcript}"
    )
    resp = context_llm.invoke(prompt)
    return json.dumps({"summary": resp.content.strip()})


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    search_hcp_history,
    search_materials_and_samples,
    suggest_follow_ups,
    summarize_voice_note,
]