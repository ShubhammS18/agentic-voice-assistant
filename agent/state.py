from typing import TypedDict

class AgentState(TypedDict):
    transcript: str
    sub_queries: list[str]
    conversation_history: list[dict]
    route: str              
    memory_hint: str
    tool_result: str
    tool_latency_ms: int
    response_text: str
    llm_ttft_ms: int
    agent_decision_ms: int  
    route_reason: str
    error: str