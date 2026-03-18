import asyncio
from ddgs import DDGS
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
            results = list(ddgs.text(arguments['query'], max_results=3))
            print(f'[DEBUG] DDG raw results count: {len(results)}', flush=True)
            print(f'[DEBUG] DDG first result: {results[0] if results else "EMPTY"}', flush=True)
            return results
    results = await asyncio.to_thread(_search)
    snippets = [f"{r['title']}: {r['body'][:200]}" for r in results]
    combined = ' '.join(snippets)
    print(f'[DEBUG] combined length: {len(combined)}', flush=True)
    return [types.TextContent(type='text', text=combined)]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == '__main__':
    asyncio.run(main())