import pytest
import asyncio
from mcp_servers.data_server import DATA_STORE


def test_data_store_has_required_keys():
    """DATA_STORE must have all expected keys."""
    required_keys = [
        'tech_stack',
        'latency_budget',
        'supported_languages',
        'routing_method',
        'web_search_provider']
    for key in required_keys:
        assert key in DATA_STORE, f"Missing key: {key}"


def test_data_store_values_non_empty():
    """All DATA_STORE values must be non-empty strings."""
    for key, value in DATA_STORE.items():
        assert isinstance(value, str), f"Key {key} is not a string"
        assert len(value) > 0, f"Key {key} has empty value"


def test_data_store_tech_stack_mentions_core_components():
    """Tech stack entry should mention core components."""
    tech = DATA_STORE['tech_stack'].lower()
    assert 'deepgram' in tech
    assert 'haiku' in tech or 'claude' in tech
    assert 'faiss' in tech


def test_data_store_routing_method_mentions_semantic():
    """Routing method entry should describe semantic approach."""
    routing = DATA_STORE['routing_method'].lower()
    assert 'semantic' in routing or 'embedding' in routing or 'faiss' in routing


@pytest.mark.asyncio
async def test_websearch_server_imports_cleanly():
    """Web search server should import without errors."""
    from mcp_servers.websearch_server import server
    assert server is not None
    assert server.name == 'web-search-tool'


@pytest.mark.asyncio
async def test_rag_server_imports_cleanly():
    """RAG server should import without errors.
    Note: actual tool calls require CRAG running on localhost:8000.
    """
    from mcp_servers.rag_server import server
    assert server is not None
    assert server.name == 'rag-tool'


@pytest.mark.asyncio
async def test_data_server_imports_cleanly():
    """Data server should import without errors."""
    from mcp_servers.data_server import server
    assert server is not None
    assert server.name == 'data-lookup-tool'