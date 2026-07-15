"""
The LangGraph agent that powers the "Log HCP Interaction" chat panel.

Role of the agent:
  The agent sits behind the conversational side of the Log Interaction Screen.
  A field rep can type (or speak, transcribed to text) a free-form note like
  "Met Dr. Sharma, discussed OncoBoost efficacy, shared Phase III data,
  she seemed positive, follow up in 2 weeks." The agent (1) decides which
  tool the request maps to (log vs edit vs lookup vs follow-up suggestion),
  (2) calls that tool, which internally uses the LLM again for structured
  extraction, and (3) turns the tool's JSON result back into a short,
  human-readable confirmation for the rep. It is the reasoning layer that
  turns unstructured field chatter into structured CRM rows, and keeps the
  structured form and the chat panel in sync (same DB, same Interaction rows).

Graph shape: a minimal ReAct-style loop -
  START -> agent (LLM decides to call a tool or respond) -> tools -> agent -> END
"""
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage

from app.agent.llm import chat_llm
from app.agent.tools import ALL_TOOLS

SYSTEM_PROMPT = """You are the AI assistant embedded in a pharma CRM's
"Log HCP Interaction" screen, used by field sales reps.

Your job:
- If the rep describes a visit/call to log, call the `log_interaction` tool
  with their raw text.
- If the rep asks to change something about an interaction already logged in
  this session, call `edit_interaction` (you will have the interaction_id
  from the earlier `log_interaction` tool result in the conversation).
- If they ask about a doctor's history/past visits, call `get_interaction_history`.
- If they're typing a doctor's name and want a match, call `search_hcp`.
- After logging an interaction, proactively call `suggest_followups` once so
  the rep sees recommended next steps.
- Always reply in 1-3 short sentences, confirming what was logged/changed in
  plain language (never dump raw JSON at the user).
"""

llm_with_tools = chat_llm.bind_tools(ALL_TOOLS)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def call_model(state: AgentState):
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


hcp_agent = build_graph()
