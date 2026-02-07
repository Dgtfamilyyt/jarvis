import pytest
from jarvis_core.skills import web_ops
from jarvis_core import config


def test_scraping_disabled(monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_SCRAPING', False)
    out = web_ops.scrape_url('http://example.com')
    assert "disabled" in out.lower()


def test_scrape_example_com(monkeypatch):
    # Enable scraping and relax robots check for test
    monkeypatch.setattr(config, 'ENABLE_SCRAPING', True)
    monkeypatch.setattr(config, 'SCRAPING_RESPECT_ROBOTS', False)
    out = web_ops.scrape_url('http://example.com', max_chars=1000)
    assert isinstance(out, str)
    assert 'Example Domain' in out or 'example domain' in out.lower()


def test_fetch_links(monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_SCRAPING', True)
    monkeypatch.setattr(config, 'SCRAPING_RESPECT_ROBOTS', False)
    links = web_ops.fetch_links('http://example.com')
    assert isinstance(links, list)
    # example.com may link externally; assert we found at least one absolute URL
    assert len(links) > 0
    assert all(l.startswith('http') for l in links)
