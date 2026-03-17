import asyncio
from duckduckgo_search import DDGS
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

server = Server('web-search-tool')

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(
        name='search_web',
        description='Search the web for current information, recent news, or facts not in the document knowledge base. Use for anything requiring up-to-date information.',
        inputSchema={
            'type': 'object',
            'properties': {'query': {'type': 'string'}},
            'required': ['query']})]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != 'search_web':
        raise ValueError(f'Unknown tool: {name}')
    def _search():
        with DDGS() as ddgs:
            return list(ddgs.text(arguments['query'], max_results=3))
    results = await asyncio.to_thread(_search)
    snippets = [f"{r['title']}: {r['body'][:200]}" for r in results]
    return [types.TextContent(type='text', text=' '.join(snippets))]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == '__main__':
    asyncio.run(main())