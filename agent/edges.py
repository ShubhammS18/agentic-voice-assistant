from agent.state import AgentState

def route_to_tool(state: AgentState) -> str:
    """Conditional edge — returns which node to go to next."""
    route = state.get('route', 'direct')
    if route == 'rag':
        return 'call_rag'
    elif route == 'web':
        return 'call_web'
    elif route == 'data':
        return 'call_data'
    else:
        return 'synthesize'  # direct — no tool call needed