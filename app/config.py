from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    deepgram_api_key: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str = 'Xb7hH8MSUJpSbSDYk0k2'
    tavily_api_key: str
    langchain_api_key: str = ''
    langchain_tracing_v2: str = 'false'
    langchain_project: str = 'agentic-voice-assistant'


    llm_model: str = 'claude-haiku-4-5-20251001'
    asr_model: str = 'nova-2'
    # Use turbo on free tier. Switch to eleven_flash_v2_5 if on paid plan.
    tts_model: str = 'eleven_turbo_v2_5'


    rag_mcp_port: int = 8001
    websearch_mcp_port: int = 8002
    data_mcp_port: int = 8003


    asr_timeout_ms: int = 5000
    agent_timeout_ms: int = 50000
    llm_timeout_ms: int = 8000
    tts_timeout_ms: int = 3000
    total_latency_budget_ms: int = 1800


    voice_system_prompt: str = (
        'You are a helpful, concise voice assistant. '
        'Keep responses to 2-3 sentences. '
        'Never use markdown or bullet points. Speak naturally.')


    class Config:
        env_file = '.env'


settings = Settings()
