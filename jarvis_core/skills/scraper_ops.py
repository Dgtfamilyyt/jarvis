import requests
from typing import Dict, List
from urllib.parse import urljoin, urlparse
import json


class ScraperSkills:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        print("Web Scraper Skills loaded")

    def fetch_page(self, url: str, extract_text_only: bool = True) -> str:
        """Fetch a web page and optionally extract text content."""
        if not url:
            return "No URL provided."
        
        if not url.startswith("http"):
            url = f"https://{url}"
        
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            if extract_text_only:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.content, "html.parser")
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    text = soup.get_text()
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = "\n".join(chunk for chunk in chunks if chunk)
                    
                    if len(text) > 3000:
                        return text[:3000] + "\n... (truncated)"
                    return text
                except ImportError:
                    return resp.text[:3000] + "... (install beautifulsoup4 for better parsing)"
            else:
                return resp.text[:3000]
        except requests.exceptions.RequestException as e:
            return f"Failed to fetch page: {e}"
        except Exception as e:
            return f"Error: {e}"

    def search_information(self, query: str) -> str:
        """Search for information using DuckDuckGo (no API key needed)."""
        if not query:
            return "No search query provided."
        
        try:
            import re
            # Use DuckDuckGo HTML search (basic approach)
            url = f"https://html.duckduckgo.com/?q={query}"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            # Parse results (simplified)
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.content, "html.parser")
                results = []
                
                for result in soup.find_all("div", class_="result", limit=5):
                    title_elem = result.find("a", class_="result__url")
                    snippet_elem = result.find("a", class_="result__snippet")
                    
                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True)
                        results.append(f"{title}: {snippet}")
                
                if results:
                    return "\n".join(results)
                else:
                    return "No results found."
            except ImportError:
                return "Install beautifulsoup4 for better search parsing."
        except Exception as e:
            return f"Search failed: {e}"

    def extract_links(self, url: str) -> str:
        """Extract all links from a web page."""
        if not url:
            return "No URL provided."
        
        if not url.startswith("http"):
            url = f"https://{url}"
        
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.content, "html.parser")
                links = []
                
                for link in soup.find_all("a", limit=20):
                    href = link.get("href")
                    text = link.get_text(strip=True)
                    
                    if href:
                        full_url = urljoin(url, href)
                        if text:
                            links.append(f"{text}: {full_url}")
                        else:
                            links.append(full_url)
                
                if links:
                    return "\n".join(links)
                else:
                    return "No links found."
            except ImportError:
                return "Install beautifulsoup4 to extract links."
        except Exception as e:
            return f"Failed to extract links: {e}"

    def extract_headings(self, url: str) -> str:
        """Extract all headings from a web page."""
        if not url:
            return "No URL provided."
        
        if not url.startswith("http"):
            url = f"https://{url}"
        
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.content, "html.parser")
                headings = []
                
                for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    for heading in soup.find_all(tag):
                        text = heading.get_text(strip=True)
                        if text:
                            headings.append(f"[{tag.upper()}] {text}")
                
                if headings:
                    return "\n".join(headings[:20])
                else:
                    return "No headings found."
            except ImportError:
                return "Install beautifulsoup4 to extract headings."
        except Exception as e:
            return f"Failed to extract headings: {e}"

    def get_page_title(self, url: str) -> str:
        """Get the title of a web page."""
        if not url:
            return "No URL provided."
        
        if not url.startswith("http"):
            url = f"https://{url}"
        
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.content, "html.parser")
                title = soup.find("title")
                
                if title:
                    return f"Title: {title.get_text(strip=True)}"
                else:
                    return "No title found on page."
            except ImportError:
                return "Install beautifulsoup4 to extract titles."
        except Exception as e:
            return f"Failed to get title: {e}"


_scraper_skills = ScraperSkills()


def execute_function(payload: Dict):
    """Route scraper operations."""
    tool = payload.get("tool", "")
    
    if tool.endswith("fetch_page") or tool.endswith("fetch"):
        url = payload.get("url") or payload.get("webpage") or ""
        extract = payload.get("extract_text_only", True)
        return _scraper_skills.fetch_page(url, extract)
    
    if tool.endswith("search_information") or tool.endswith("search_info") or tool.endswith("search"):
        query = payload.get("query") or payload.get("search") or ""
        return _scraper_skills.search_information(query)
    
    if tool.endswith("extract_links") or tool.endswith("links"):
        url = payload.get("url") or payload.get("webpage") or ""
        return _scraper_skills.extract_links(url)
    
    if tool.endswith("extract_headings") or tool.endswith("headings"):
        url = payload.get("url") or payload.get("webpage") or ""
        return _scraper_skills.extract_headings(url)
    
    if tool.endswith("get_page_title") or tool.endswith("page_title"):
        url = payload.get("url") or payload.get("webpage") or ""
        return _scraper_skills.get_page_title(url)
    
    return f"Unknown scraper tool: {tool}"
