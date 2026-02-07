from jarvis_core import config
from jarvis_core.skills import web_ops


def test_web_search_duckduckgo_enabled(monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_SCRAPING', True)
    monkeypatch.setattr(config, 'SEARCH_PROVIDER', 'duckduckgo')
    results = web_ops.web_search('openai', max_results=3)
    assert isinstance(results, list)
    # DuckDuckGo instant answer should return at least one item for a common query
    assert len(results) > 0
    # Each result should have title and url keys
    for r in results:
        assert 'title' in r and 'url' in r


def test_web_search_disabled(monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_SCRAPING', False)
    results = web_ops.web_search('example domain', max_results=3)
    assert results == []
