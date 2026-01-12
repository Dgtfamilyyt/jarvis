import webbrowser


def search_web(query: str):
    if not query:
        return "No query provided"
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Searched web for {query}"
