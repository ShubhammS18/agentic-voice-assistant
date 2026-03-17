from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agent.state import AgentState
from agent.nodes import (
    orchestrator_node,
    call_rag_node,
    call_web_node,
    call_data_node,
    synthesize_node)
from agent.edges import route_to_tool


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node('orchestrator', orchestrator_node)
    graph.add_node('call_rag', call_rag_node)
    graph.add_node('call_web', call_web_node)
    graph.add_node('call_data', call_data_node)
    graph.add_node('synthesize', synthesize_node)

    graph.set_entry_point('orchestrator')

    graph.add_conditional_edges('orchestrator',route_to_tool,
            {'call_rag': 'call_rag',
            'call_web': 'call_web',
            'call_data': 'call_data',
            'synthesize': 'synthesize'})

    graph.add_edge('call_rag', 'synthesize')
    graph.add_edge('call_web', 'synthesize')
    graph.add_edge('call_data', 'synthesize')
    graph.add_edge('synthesize', END)

    return graph.compile(checkpointer=MemorySaver())


agent_graph = build_graph()
