import json
from typing import Tuple, Optional
from jarvis_core import config


def _function_definitions():
    """Return a list of function definitions compatible with OpenAI function-calling.
    Names match the skill module paths so the orchestrator can route calls.
    """
    return [
        {
            "name": "system_ops.open_app",
            "description": "Open an application by name or URL on the host machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Application name or URL to open"}
                },
                "required": ["name"],
            },
        },
        {
            "name": "web_ops.search_web",
            "description": "Search the web for the provided query and open a browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
        {
            "name": "media_ops.play_music",
            "description": "Play a music file from disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the music file"}
                },
                "required": [],
            },
        },
    ]


def _heuristic_parse(user_text: str) -> Tuple[str, dict]:
    t = user_text.strip().lower()
    if t.startswith("open ") or t.startswith("launch "):
        name = user_text.split(maxsplit=1)[1] if len(user_text.split()) > 1 else ""
        return "function_call", {"tool": "system_ops.open_app", "name": name}

    if t.startswith("search ") or t.startswith("look up "):
        query = user_text.split(maxsplit=1)[1] if len(user_text.split()) > 1 else ""
        return "function_call", {"tool": "web_ops.search_web", "query": query}

    if "play" in t and ("music" in t or t.endswith("mp3") or "play " in t):
        # try to extract a path or fallback to default
        parts = user_text.split(" ", 1)
        arg = parts[1] if len(parts) > 1 else None
        return "function_call", {"tool": "media_ops.play_music", "path": arg}

    return "conversation", f"Echo: {user_text}"


class Brain:
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.system_prompt = {
            "role": "system",
            "content": (
                "You are Jarvis, an advanced AI assistant. "
                "Your responses must be short, precise, and conversational. "
                "Do not use markdown, lists, or code blocks unless explicitly asked. "
                "Keep answers under 2 sentences when possible."
            ),
        }
        self.messages = [self.system_prompt]

        # Try to import ollama; if not present we'll fall back to other backends
        try:
            import ollama

            self._ollama = ollama
        except Exception:
            self._ollama = None

    def think(self, user_text: str) -> str:
        """Return a short assistant response. Uses Ollama if available, else
        falls back to the module `process_command` logic for a quick reply.
        """
        # Prefer Ollama for conversational replies
        if self._ollama:
            self.messages.append({"role": "user", "content": user_text})
            try:
                resp = self._ollama.chat(model=self.model, messages=self.messages)
                reply = resp.get("message", {}).get("content", "")
                self.messages.append({"role": "assistant", "content": reply})
                return reply
            except Exception as e:
                print(f"Ollama error in Brain.think: {e}")

        # Fall back to existing process_command behavior for a safe reply
        try:
            rtype, payload = process_command(user_text)
            if rtype == "conversation":
                return payload
            # If it's a function call, produce a short natural-language summary
            tool = payload.get("tool")
            args = {k: v for k, v in payload.items() if k != "tool"}
            if args:
                return f"I will call {tool} with {args}"
            return f"I will call {tool}"
        except Exception as e:
            print(f"Brain fallback error: {e}")
            return "I am having trouble connecting to my neural network, sir."

    def clear_memory(self):
        self.messages = [self.system_prompt]


def process_command(user_text: str, memory: Optional[object] = None) -> Tuple[str, dict]:
    """Process user text and return either a function call payload or conversation.

    Strategy:
    - First run a lightweight heuristic parser to detect direct commands (function calls).
    - If a function call is detected, return it immediately so the orchestrator can execute.
    - Otherwise, prefer a local Ollama model (if `ollama` is installed) as the Brain.
    - If Ollama is unavailable, fall back to OpenAI function-calling (if API key present).
    - If all remote/advanced options fail, return a simple echo conversation.
    """
    # 1) Heuristic quick-check for tool use
    heuristic_type, heuristic_payload = _heuristic_parse(user_text)
    if heuristic_type == "function_call":
        return heuristic_type, heuristic_payload

    # 2) Try Ollama-based local Brain if available
    try:
        import ollama

        class Brain:
            def __init__(self, model: str = "llama3.2"):
                self.model = model
                self.system_prompt = {
                    "role": "system",
                    "content": (
                        "You are Jarvis, an advanced AI assistant. "
                        "Your responses must be short, precise, and conversational. "
                        "Do not use markdown, lists, or code blocks unless explicitly asked. "
                        "Keep answers under 2 sentences when possible."
                    ),
                }
                self.messages = [self.system_prompt]

            def think(self, user_text: str) -> str:
                self.messages.append({"role": "user", "content": user_text})
                try:
                    resp = ollama.chat(model=self.model, messages=self.messages)
                    reply = resp.get("message", {}).get("content", "")
                    self.messages.append({"role": "assistant", "content": reply})
                    return reply
                except Exception as e:
                    print(f"Ollama error: {e}")
                    return ""

            def clear_memory(self):
                self.messages = [self.system_prompt]

        # Use a module-level singleton Brain to preserve chat context
        if not hasattr(process_command, "_brain"):
            process_command._brain = Brain()

        reply = process_command._brain.think(user_text)
        return "conversation", reply

    except Exception:
        # Ollama not available; try OpenAI function calling if API key exists
        api_key = config.OPENAI_API_KEY
        if not api_key:
            # Final fallback: echo
            return "conversation", f"Echo: {user_text}"

        try:
            import openai
            openai.api_key = api_key

            messages = [
                {"role": "system", "content": "You are Jarvis, a helpful assistant that must use provided functions for actionable tasks."},
                {"role": "user", "content": user_text},
            ]

            functions = _function_definitions()

            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=messages,
                functions=functions,
                function_call="auto",
                max_tokens=512,
            )

            choice = resp["choices"][0]["message"]

            if choice.get("function_call"):
                fname = choice["function_call"]["name"]
                args_text = choice["function_call"].get("arguments", "{}")
                try:
                    args = json.loads(args_text)
                except Exception:
                    args = {"raw": args_text}

                payload = {"tool": fname}
                payload.update(args)
                return "function_call", payload

            content = choice.get("content") or choice.get("text") or ""
            return "conversation", content

        except Exception as e:
            print(f"LLM client error: {e}")
            return "conversation", f"Echo: {user_text}"
