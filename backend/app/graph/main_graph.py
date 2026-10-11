from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.graph.nodes.failure import failure_node
from app.graph.nodes.generate import generate_node
from app.graph.nodes.guard import guard_node
from app.graph.nodes.memory_load import load_contextual_node, load_longterm_node
from app.graph.nodes.memory_update import memory_update_node
from app.graph.state import ChatState
from app.graph.subgraphs.research import research_graph

PARALLEL = ["research", "load_longterm", "load_contextual"]


async def decide_node(state: dict) -> dict:
    """Join point: runs once research and both memory loads are finished.
    Images are sent here, once, so they always appear BEFORE the answer text."""
    if state.get("found") and state.get("images"):
        get_stream_writer()({"event": "images", "data": {"images": state["images"]}})
    return {}


def _after_guard(state: dict) -> list[str]:
    return ["failure"] if state.get("fail_code") else PARALLEL


def _after_decide(state: dict) -> str:
    return "generate" if state.get("found") else "failure"


def build_graph(checkpointer=None):
    g = StateGraph(ChatState)
    g.add_node("guard", guard_node)
    g.add_node("research", research_graph)      
    g.add_node("load_longterm", load_longterm_node)
    g.add_node("load_contextual", load_contextual_node)
    g.add_node("decide", decide_node)
    g.add_node("generate", generate_node)
    g.add_node("memory_update", memory_update_node)
    g.add_node("failure", failure_node)

    g.add_edge(START, "guard")
    g.add_conditional_edges("guard", _after_guard, ["failure", *PARALLEL])  
    g.add_edge(PARALLEL, "decide")     
    g.add_conditional_edges("decide", _after_decide, ["generate", "failure"])
    g.add_edge("generate", "memory_update")
    g.add_edge("memory_update", END)
    g.add_edge("failure", END)
    return g.compile(checkpointer=checkpointer)


guest_graph = build_graph() 
_user_graph = None


def init_user_graph(saver) -> None:
    global _user_graph
    _user_graph = build_graph(saver)


def get_user_graph():
    if _user_graph is None:
        raise RuntimeError("User graph not initialised (startup not finished)")
    return _user_graph