from datetime import date
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.agent.llm import primary_llm
from app.agent.tools import ALL_TOOLS


def get_system_prompt() -> SystemMessage:
    today = date.today().strftime("%Y-%m-%d")

    return SystemMessage(
        content=f"""
You are the AI assistant embedded in a pharma field rep's CRM, on the
'Log HCP Interaction' screen.

Today's actual date is {today}. This date comes from the server clock and is
the authoritative current date.

When the user says:
- today
- yesterday
- tomorrow
- this week
- this month
- last week
- next week

interpret them relative to today's date above.

Never invent or assume a different current date.

Your job is to turn a rep's natural-language description of a visit/call/email
with a healthcare professional (HCP) into a structured logged record.

Always extract:
- HCP name
- interaction type
- date
- attendees
- topics discussed
- sentiment
- materials shared
- samples distributed
- outcomes
- follow-up actions

If the HCP name is missing, ask for it before logging.

Use search_hcp_history when it would help you avoid repeating stale talking
points or catch overdue follow-ups.

After logging, call suggest_follow_ups and present them briefly.

Be concise and confirm what was recorded in plain language.
"""
    )


llm_with_tools = primary_llm.bind_tools(ALL_TOOLS)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def agent_node(state: AgentState):
    system_prompt = get_system_prompt()

    messages = [
        system_prompt,
        *state["messages"],
    ]

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response]
    }


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END


tool_node = ToolNode(ALL_TOOLS)

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END},
)
workflow.add_edge("tools", "agent")

hcp_agent_graph = workflow.compile()