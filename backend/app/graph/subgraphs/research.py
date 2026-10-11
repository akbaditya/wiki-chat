from langgraph.graph import END, START, StateGraph

from app.graph.nodes.analyze import analyze_node
from app.graph.nodes.grade import grade_node
from app.graph.state import ResearchState
from app.graph.subgraphs.query_transform import transform_graph
from app.graph.subgraphs.retrieval import retrieval_graph


def _after_analyze(state: dict) -> str:
    return "transform" if state.get("strategy", "none") != "none" else "retrieval"


def _after_grade(state: dict) -> str:
    return "transform" if state.get("retry") else END


def build_research_graph():
    g = StateGraph(ResearchState)
    g.add_node("analyze", analyze_node)
    g.add_node("transform", transform_graph) 
    g.add_node("retrieval", retrieval_graph) 
    g.add_node("grade", grade_node)

    g.add_edge(START, "analyze")
    g.add_conditional_edges("analyze", _after_analyze, ["transform", "retrieval"])
    g.add_edge("transform", "retrieval")
    g.add_edge("retrieval", "grade")
    g.add_conditional_edges("grade", _after_grade, ["transform", END])
    return g.compile()


research_graph = build_research_graph()