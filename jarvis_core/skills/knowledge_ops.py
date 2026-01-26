import requests
from typing import Dict
import xml.etree.ElementTree as ET


class KnowledgeSkills:
    def __init__(self):
        print("Knowledge Skills loaded")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_wikipedia_summary(self, topic: str) -> str:
        """Fetch a brief summary from Wikipedia."""
        if not topic:
            return "No topic specified."
        
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            if "extract" in data:
                summary = data["extract"]
                if len(summary) > 2000:
                    return summary[:2000] + "... (truncated)"
                return summary
            else:
                return f"No summary found for '{topic}'."
        except requests.exceptions.HTTPError:
            return f"Topic '{topic}' not found on Wikipedia."
        except Exception as e:
            return f"Failed to fetch Wikipedia summary: {e}"

    def get_news_headlines(self, category: str = "general") -> str:
        """Fetch recent news headlines (uses Hacker News as a fallback)."""
        if not category:
            category = "general"
        
        try:
            # Use Hacker News API as a free alternative
            url = "https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            story_ids = resp.json()[:10]  # Get top 10
            headlines = []
            
            for story_id in story_ids:
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json?print=pretty"
                try:
                    story_resp = self.session.get(story_url, timeout=5)
                    story = story_resp.json()
                    title = story.get("title", "")
                    if title:
                        headlines.append(title)
                except Exception:
                    continue
            
            if headlines:
                return "Top Headlines:\n" + "\n".join(f"- {h}" for h in headlines)
            else:
                return "Could not fetch headlines."
        except Exception as e:
            return f"Failed to fetch news: {e}"

    def lookup_definition(self, word: str) -> str:
        """Look up the definition of a word using Free Dictionary API."""
        if not word:
            return "No word specified."
        
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            if isinstance(data, list) and data:
                entry = data[0]
                meanings = entry.get("meanings", [])
                
                result = [f"Word: {entry.get('word', word)}"]
                
                for meaning in meanings[:2]:  # Limit to first 2 meanings
                    pos = meaning.get("partOfSpeech", "unknown")
                    definitions = meaning.get("definitions", [])
                    result.append(f"\n[{pos}]")
                    
                    for defn in definitions[:2]:  # Limit to first 2 definitions
                        definition = defn.get("definition", "")
                        result.append(f"- {definition}")
                
                return "\n".join(result)
            else:
                return f"No definition found for '{word}'."
        except requests.exceptions.HTTPError:
            return f"Word '{word}' not found."
        except Exception as e:
            return f"Failed to look up definition: {e}"

    def get_quote_of_the_day(self) -> str:
        """Fetch a random inspirational quote."""
        try:
            url = "https://api.quotable.io/random"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            quote = data.get("content", "")
            author = data.get("author", "Unknown")
            
            return f'"{quote}" — {author}'
        except Exception as e:
            return f"Failed to fetch quote: {e}"

    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> str:
        """Convert between currencies using live exchange rates."""
        if not from_currency or not to_currency:
            return "Both currencies required."
        
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            rates = data.get("rates", {})
            rate = rates.get(to_currency.upper())
            
            if rate:
                result = amount * rate
                return f"{amount} {from_currency.upper()} = {result:.2f} {to_currency.upper()}"
            else:
                return f"Currency '{to_currency}' not found."
        except Exception as e:
            return f"Currency conversion failed: {e}"


_knowledge_skills = KnowledgeSkills()


def execute_function(payload: Dict):
    """Route knowledge operations."""
    tool = payload.get("tool", "")
    
    if tool.endswith("get_wikipedia_summary") or tool.endswith("wikipedia"):
        topic = payload.get("topic") or payload.get("query") or ""
        return _knowledge_skills.get_wikipedia_summary(topic)
    
    if tool.endswith("get_news_headlines") or tool.endswith("news"):
        category = payload.get("category") or "general"
        return _knowledge_skills.get_news_headlines(category)
    
    if tool.endswith("lookup_definition") or tool.endswith("definition"):
        word = payload.get("word") or payload.get("term") or ""
        return _knowledge_skills.lookup_definition(word)
    
    if tool.endswith("get_quote_of_the_day") or tool.endswith("quote"):
        return _knowledge_skills.get_quote_of_the_day()
    
    if tool.endswith("convert_currency") or tool.endswith("currency"):
        amount = payload.get("amount", 1)
        from_curr = payload.get("from") or payload.get("from_currency") or ""
        to_curr = payload.get("to") or payload.get("to_currency") or ""
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 1
        return _knowledge_skills.convert_currency(amount, from_curr, to_curr)
    
    return f"Unknown knowledge tool: {tool}"
