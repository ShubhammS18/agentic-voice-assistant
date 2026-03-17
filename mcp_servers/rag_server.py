import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

server = Server('rag-tool')

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(
        name='ask_documents',
        description='Query the internal knowledge base. Use for questions about company policy, product docs, technical guides, or any domain knowledge stored in indexed documents.',
        inputSchema={
            'type': 'object',
            'properties': {'query': {'type': 'string', 'description': 'The question to answer'}},
            'required': ['query']})]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != 'ask_documents':
        raise ValueError(f'Unknown tool: {name}')
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            'http://localhost:8000/ask',
            json={'question': arguments['query']})
        data = response.json()
    result = f"{data['answer']} (verdict: {data['verdict']})"
    return [types.TextContent(type='text', text=result)]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == '__main__':
    asyncio.run(main())