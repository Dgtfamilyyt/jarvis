import webbrowser
import requests
from urllib.parse import urlparse, urljoin
import urllib.robotparser
from bs4 import BeautifulSoup
from .. import config


def search_web(query: str):
    if not query:
        return "No query provided"
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Searched web for {query}"


def _allowed_by_robots(url: str) -> bool:
    """Check robots.txt for the given URL using configured user-agent.
    If `SCRAPING_RESPECT_ROBOTS` is False, always allow.
    On fetch errors, default to False (safer) unless explicitly disabled by config.
    """
    if not config.SCRAPING_RESPECT_ROBOTS:
        return True
    try:
        p = urlparse(url)
        robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(config.SCRAPING_USER_AGENT, url)
    except Exception:
        return False


def _fetch_raw(url: str, timeout: float = None, max_bytes: int = None) -> (bytes, str):
    """Fetch URL with streaming and limit total bytes. Returns (content_bytes, content_type)
    Raises requests.RequestException on network errors.
    """
    timeout = timeout or config.SCRAPING_TIMEOUT
    max_bytes = max_bytes or config.SCRAPING_MAX_BYTES
    headers = {"User-Agent": config.SCRAPING_USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    chunks = []
    total = 0
    for chunk in resp.iter_content(chunk_size=8192):
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            # stop reading more to avoid huge downloads
            break
        chunks.append(chunk)
    return b"".join(chunks), content_type


def scrape_url(url: str, max_chars: int = 10000) -> str:
    """Fetch and extract visible text from a webpage.
    - Requires `ENABLE_SCRAPING` in `config.py` to be True.
    - Respects robots.txt by default.
    - Returns a plain-text excerpt (title + body) up to `max_chars`.
    """
    if not config.ENABLE_SCRAPING:
        return "Web scraping is disabled (set ENABLE_SCRAPING=true to enable)."

    try:
        # Normalize URL
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "http://" + url
        # Check robots
        if not _allowed_by_robots(url):
            return "Scraping disallowed by robots.txt or robots check failed."
        raw, ctype = _fetch_raw(url)
    except requests.RequestException as e:
        return f"Network error fetching URL: {e}"
    except Exception as e:
        return f"Error fetching URL: {e}"

    # Only parse HTML-like content
    if "html" not in (ctype or "").lower():
        # Return first chunk of non-HTML content-type
        try:
            text_preview = raw.decode('utf-8', errors='replace')
            return text_preview[:max_chars]
        except Exception:
            return "Fetched non-HTML content (binary)."

    try:
        soup = BeautifulSoup(raw, "lxml")
        # Remove scripts/styles and hidden elements
        for s in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'aside']):
            s.decompose()
        # Extract visible text
        text = soup.get_text(separator=' ', strip=True)
        # Collapse whitespace
        text = ' '.join(text.split())
        if not text:
            return "No visible text extracted from page."
        # Optionally include title
        title = (soup.title.string.strip() if soup.title and soup.title.string else None)
        if title:
            out = f"Title: {title}\n\n{text}"
        else:
            out = text
        return out[:max_chars]
    except Exception as e:
        return f"Failed to parse HTML: {e}"


def fetch_links(url: str, max_links: int = 20) -> list:
    """Return a list of absolute links found on the page (up to max_links).
    Respects same enable/robots settings as `scrape_url`.
    """
    if not config.ENABLE_SCRAPING:
        return []
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "http://" + url
        if not _allowed_by_robots(url):
            return []
        raw, ctype = _fetch_raw(url)
    except Exception:
        return []
    if "html" not in (ctype or "").lower():
        return []
    try:
        soup = BeautifulSoup(raw, "lxml")
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # build absolute URL
            abs_url = urljoin(url, href)
            links.append(abs_url)
            if len(links) >= max_links:
                break
        return links
    except Exception:
        return []


def _search_duckduckgo(query: str, max_results: int = 5) -> list:
    """Use DuckDuckGo Instant Answer API as a lightweight search fallback (no API key required).
    Returns a list of dicts: {title, snippet, url}. This is not a full web index but provides
    useful related topics and instant answers.
    """
    try:
        url = 'https://api.duckduckgo.com/'
        params = {'q': query, 'format': 'json', 'no_html': 1, 'skip_disambig': 1}
        headers = {"User-Agent": config.SCRAPING_USER_AGENT}
        resp = requests.get(url, params=params, headers=headers, timeout=config.SCRAPING_TIMEOUT)
        resp.raise_for_status()
        j = resp.json()
        results = []
        # Primary abstract
        abstract = j.get('AbstractText') or ''
        abstract_url = j.get('AbstractURL') or ''
        if abstract:
            results.append({'title': j.get('Heading') or query, 'snippet': abstract, 'url': abstract_url})
        # RelatedTopics (can be nested)
        for item in j.get('RelatedTopics', []):
            if len(results) >= max_results:
                break
            if 'Text' in item and 'FirstURL' in item:
                results.append({'title': item.get('Text','').split(' - ')[0], 'snippet': item.get('Text',''), 'url': item.get('FirstURL','')})
            elif 'Topics' in item:
                for sub in item.get('Topics', []):
                    if len(results) >= max_results:
                        break
                    if 'Text' in sub and 'FirstURL' in sub:
                        results.append({'title': sub.get('Text','').split(' - ')[0], 'snippet': sub.get('Text',''), 'url': sub.get('FirstURL','')})
        # Trim to max_results
        return results[:max_results]
    except Exception as e:
        print(f"[SEARCH] DuckDuckGo Instant Answer failed: {e}", flush=True)
        return []


def _search_bing(query: str, max_results: int = 5) -> list:
    """Use Bing Web Search API (requires subscription key). Returns same format as _search_duckduckgo.
    """
    if not config.BING_SUBSCRIPTION_KEY:
        print('[SEARCH] Bing key missing', flush=True)
        return []
    try:
        headers = {"Ocp-Apim-Subscription-Key": config.BING_SUBSCRIPTION_KEY}
        params = {"q": query, "count": max_results}
        resp = requests.get(config.BING_ENDPOINT, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        j = resp.json()
        results = []
        for v in j.get('webPages', {}).get('value', []):
            results.append({'title': v.get('name', ''), 'snippet': v.get('snippet', ''), 'url': v.get('url', '')})
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"[SEARCH] Bing search failed: {e}", flush=True)
        return []


def web_search(query: str, max_results: int = 5, provider: str = None) -> list:
    """Public web search function. Choose provider via `provider` arg or `config.SEARCH_PROVIDER`.
    Returns list of {title,snippet,url} objects.
    """
    if not config.ENABLE_SCRAPING:
        return []
    if not query:
        return []
    provider = (provider or config.SEARCH_PROVIDER or 'duckduckgo').lower()
    if provider == 'bing':
        return _search_bing(query, max_results=max_results)
    # default to duckduckgo
    return _search_duckduckgo(query, max_results=max_results)
