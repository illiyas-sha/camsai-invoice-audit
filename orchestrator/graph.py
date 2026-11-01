"""LangGraph StateGraph: wires Agent1 -> Agent2 -> (conditional) Agent3 branches, builds the compiled graph.

Routing:
  agent1 --error--> agent3_error            agent1 --ok--> agent2
  agent2 --error--> agent3_error
  agent2 --compliant--> agent3_post         agent2 --anomalous--> agent3_escalate
  agent3_post/agent3_escalate --error--> agent3_error (notify failed partway through)
  agent3_post/agent3_escalate --ok--> END
  agent3_error --> END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.agent1_ingestion import build_agent1
from agents.agent2_validation import build_agent2
from agents.agent3_reporting import (
    build_agent3_error_notify,
    build_agent3_escalate,
    build_agent3_post_and_notify,
)
from agents.mcp_client import MCPToolClient
from agents.state import InvoiceAuditState


def _route_after_agent1(state: InvoiceAuditState) -> str:
    return "agent3_error" if state.get("error") else "agent2"


def _route_after_agent2(state: InvoiceAuditState) -> str:
    if state.get("error"):
        return "agent3_error"
    return "agent3_post" if state.get("is_compliant") else "agent3_escalate"


def _route_after_agent3_action(state: InvoiceAuditState) -> str:
    return "agent3_error" if state.get("error") else END


def build_graph(client: MCPToolClient) -> CompiledStateGraph:
    """Build and compile the invoice-audit state graph for one shared MCPToolClient session."""
    graph = StateGraph(InvoiceAuditState)

    graph.add_node("agent1", build_agent1(client))
    graph.add_node("agent2", build_agent2(client))
    graph.add_node("agent3_post", build_agent3_post_and_notify(client))
    graph.add_node("agent3_escalate", build_agent3_escalate(client))
    graph.add_node("agent3_error", build_agent3_error_notify(client))

    graph.add_edge(START, "agent1")
    graph.add_conditional_edges(
        "agent1", _route_after_agent1, {"agent2": "agent2", "agent3_error": "agent3_error"}
    )
    graph.add_conditional_edges(
        "agent2",
        _route_after_agent2,
        {"agent3_post": "agent3_post", "agent3_escalate": "agent3_escalate", "agent3_error": "agent3_error"},
    )
    graph.add_conditional_edges(
        "agent3_post", _route_after_agent3_action, {"agent3_error": "agent3_error", END: END}
    )
    graph.add_conditional_edges(
        "agent3_escalate", _route_after_agent3_action, {"agent3_error": "agent3_error", END: END}
    )
    graph.add_edge("agent3_error", END)

    return graph.compile()
