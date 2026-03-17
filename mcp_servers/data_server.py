# mcp_servers/data_server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

DATA_STORE = {
    'latency_budget': 'ASR 300ms + rewrite 65ms + route 5ms + LLM 300ms + TTS 275ms = ~945ms typical',
    'tech_stack': 'Deepgram Nova-2, Claude Haiku 4.5, ElevenLabs turbo_v2_5, LangGraph, MCP, FAISS, DuckDuckGo',
    'supported_languages': 'English only in this version',
    'routing_method': 'Semantic embedding similarity via FAISS — not LLM classification',
    'web_search_provider': 'DuckDuckGo in web server, Tavily only inside CRAG as fallback'}

server = Server('data-lookup-tool')

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(
        name='lookup_structured',
        description=f'Look up specific structured facts. Available keys: {list(DATA_STORE.keys())}',
        inputSchema={
            'type': 'object',
            'properties': {'key': {'type': 'string', 'description': 'The key to look up'}},
            'required': ['key']})]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != 'lookup_structured':
        raise ValueError(f'Unknown tool: {name}')
    key = arguments['key']
    result = DATA_STORE.get(key, f'No data found for key: {key}')
    return [types.TextContent(type='text', text=result)]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == '__main__':
    asyncio.run(main())