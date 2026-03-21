from app.router import route_query


def test_rag_routing_documents():
    """Document and policy queries should route to rag."""
    sub_queries = [
        'company visa policy requirements',
        'internal document procedures rules',
        'knowledge base technical guide']
    route, route_ms = route_query(sub_queries)
    assert route == 'rag'
    assert route_ms >= 0


def test_web_routing_current_events():
    """Current events queries should route to web."""
    sub_queries = [
        'AI news today March 2026',
        'latest artificial intelligence announcements',
        'breaking tech news current events']
    route, route_ms = route_query(sub_queries)
    assert route == 'web'
    assert route_ms >= 0


def test_data_routing_structured_facts():
    """Structured fact queries should route to data."""
    sub_queries = [
        'system tech stack components',
        'latency budget configuration values',
        'supported languages version information']
    route, route_ms = route_query(sub_queries)
    assert route == 'data'
    assert route_ms >= 0


def test_route_ms_is_fast():
    """Semantic routing should complete in under 500ms."""
    sub_queries = ['AI news today', 'latest announcements']
    _, route_ms = route_query(sub_queries)
    assert route_ms < 500


def test_single_sub_query_still_routes():
    """Router should work with just one sub-query."""
    route, _ = route_query(['what is the weather today breaking news'])
    assert route in ['rag', 'web', 'data']


def test_route_returns_valid_domain():
    """Router should always return one of the three valid domains."""
    sub_queries = ['some query about anything']
    route, _ = route_query(sub_queries)
    assert route in ['rag', 'web', 'data']