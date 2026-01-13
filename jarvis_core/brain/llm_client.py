import json
import os
import time
import math
import uuid
from typing import Tuple, Optional, List, Dict
from jarvis_core import config
from base64 import urlsafe_b64encode

try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.fernet import Fernet
    _HAS_CRYPTO = True
except Exception:
    Fernet = None
    _HAS_CRYPTO = False

# Persistent memory files (workspace root)
MEMORY_FILE = os.path.join(os.getcwd(), "jarvis_memory.json")
MEMORY_JSONL = os.path.join(os.getcwd(), "jarvis_memory.jsonl")
MEMORY_JSONL_ENC = MEMORY_JSONL + ".enc"
MEMORY_SALT = MEMORY_JSONL + ".salt"


def _now_ts() -> float:
    return time.time()


class MemoryManager:
    """Retrieval-augmented memory manager.

    Features:
    - Stores memories (text + metadata) in a JSONL file for append/streaming.
    - Keeps in-memory embeddings and supports retrieval via cosine similarity.
    - Tries to use `sentence_transformers` for embeddings, falls back to OpenAI embeddings
      if `OPENAI_API_KEY` is set, else uses a deterministic hash-based vector.
    - Supports add, forget, get_relevant, consolidate, and simple eviction.
    """

    def __init__(self, cap: int = 2000):
        self.cap = cap
        self.mem_index: List[Dict] = []  # list of memory dicts with id,text,meta,embedding
        self.embeddings = []  # list of lists (vectors)
        self._load_backends()
        self._load_from_jsonl()

    def _load_backends(self):
        self._sbert = None
        self._openai = None
        try:
            from sentence_transformers import SentenceTransformer

            self._sbert = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self._sbert = None

        if not self._sbert and config.OPENAI_API_KEY:
            try:
                import openai

                openai.api_key = config.OPENAI_API_KEY
                self._openai = openai
            except Exception:
                self._openai = None

        # encryption support
        self._fernet = None
        self._encryption_enabled = False
        if _HAS_CRYPTO:
            key_b64 = os.getenv("MEMORY_KEY") or os.getenv("MEMORY_ENCRYPTION_KEY")
            passphrase = os.getenv("MEMORY_PASSPHRASE")
            if key_b64:
                try:
                    self._fernet = Fernet(key_b64.encode() if isinstance(key_b64, str) else key_b64)
                    self._encryption_enabled = True
                except Exception:
                    self._fernet = None
            elif passphrase:
                # derive key from passphrase (store/read salt)
                try:
                    if os.path.exists(MEMORY_SALT):
                        salt = open(MEMORY_SALT, "rb").read()
                    else:
                        salt = os.urandom(16)
                        with open(MEMORY_SALT, "wb") as sf:
                            sf.write(salt)
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000, backend=default_backend()
                    )
                    key = urlsafe_b64encode(kdf.derive(passphrase.encode()))
                    self._fernet = Fernet(key)
                    self._encryption_enabled = True
                except Exception:
                    self._fernet = None
                    self._encryption_enabled = False

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if self._sbert:
            vecs = self._sbert.encode(texts, convert_to_numpy=True)
            return [v.tolist() for v in vecs]
        if self._openai:
            try:
                resp = self._openai.Embedding.create(model="text-embedding-3-small", input=texts)
                return [d["embedding"] for d in resp["data"]]
            except Exception:
                pass
        # Fallback: deterministic hash -> vector
        out = []
        for t in texts:
            h = uuid.uuid5(uuid.NAMESPACE_OID, t).int
            v = []
            # create small pseudo-random vector from hash
            for i in range(64):
                v.append(((h >> (i * 5)) & 0x1F) / 31.0)
            out.append(v)
        return out

    def _load_from_jsonl(self):
        # If encrypted file present, load/decrypt it as full JSONL content
        try:
            if self._encryption_enabled and os.path.exists(MEMORY_JSONL_ENC):
                with open(MEMORY_JSONL_ENC, "rb") as f:
                    data = f.read()
                try:
                    plain = self._fernet.decrypt(data)
                    lines = plain.decode("utf-8").splitlines()
                    for line in lines:
                        try:
                            item = json.loads(line)
                            self.mem_index.append(item)
                        except Exception:
                            continue
                except Exception as e:
                    print("[Memory] Failed to decrypt memory file:", e)
            elif os.path.exists(MEMORY_JSONL):
                with open(MEMORY_JSONL, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            item = json.loads(line)
                            self.mem_index.append(item)
                        except Exception:
                            continue

            # Rebuild embeddings
            texts = [m["text"] for m in self.mem_index]
            if texts:
                self.embeddings = self._embed(texts)
        except Exception as e:
            print("[Memory] Failed to load JSONL:", e)

    def _append_jsonl(self, item: Dict):
        try:
            if self._encryption_enabled:
                # read existing, append, write encrypted blob
                items = []
                if os.path.exists(MEMORY_JSONL_ENC):
                    try:
                        with open(MEMORY_JSONL_ENC, "rb") as ef:
                            pdata = ef.read()
                        ptext = self._fernet.decrypt(pdata).decode("utf-8")
                        for ln in ptext.splitlines():
                            try:
                                items.append(json.loads(ln))
                            except Exception:
                                continue
                    except Exception:
                        items = []
                items.append(item)
                text = "\n".join(json.dumps(it, ensure_ascii=False) for it in items)
                enc = self._fernet.encrypt(text.encode("utf-8"))
                with open(MEMORY_JSONL_ENC, "wb") as ef:
                    ef.write(enc)
            else:
                with open(MEMORY_JSONL, "a", encoding="utf-8") as f:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception as e:
            print("[Memory] Failed to append JSONL:", e)

    def add(self, text: str, tags: Optional[List[str]] = None, importance: float = 0.5, source: str = "user") -> str:
        mid = str(uuid.uuid4())
        meta = {"ts": _now_ts(), "tags": tags or [], "importance": float(importance), "source": source}
        item = {"id": mid, "text": text, "meta": meta}
        # compute embedding
        emb = self._embed([text])[0]
        self.mem_index.append(item)
        self.embeddings.append(emb)
        self._append_jsonl(item)
        self._evict_if_needed()
        return mid

    def forget(self, mid: str) -> bool:
        for i, m in enumerate(self.mem_index):
            if m.get("id") == mid:
                del self.mem_index[i]
                del self.embeddings[i]
                # rewrite jsonl file (simple approach)
                try:
                    with open(MEMORY_JSONL, "w", encoding="utf-8") as f:
                        for it in self.mem_index:
                            f.write(json.dumps(it, ensure_ascii=False) + "\n")
                except Exception as e:
                    print("[Memory] Failed to rewrite JSONL on forget:", e)
                return True
        return False

    def _cosine(self, a: List[float], b: List[float]) -> float:
        try:
            import math

            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            if na == 0 or nb == 0:
                return 0.0
            return sum(x * y for x, y in zip(a, b)) / (na * nb)
        except Exception:
            return 0.0

    def get_relevant(self, query: str, k: int = 5) -> List[Dict]:
        if not self.mem_index:
            return []
        qv = self._embed([query])[0]
        scores = []
        for i, emb in enumerate(self.embeddings):
            sc = self._cosine(qv, emb)
            scores.append((sc, i))
        scores.sort(reverse=True, key=lambda x: x[0])
        out = []
        for sc, idx in scores[:k]:
            m = self.mem_index[idx].copy()
            m["score"] = float(sc)
            out.append(m)
        return out

    def _evict_if_needed(self):
        # If over cap, evict oldest low-importance memories until under cap
        if len(self.mem_index) <= self.cap:
            return
        # sort by (importance asc, ts asc)
        order = sorted(range(len(self.mem_index)), key=lambda i: (self.mem_index[i]["meta"].get("importance", 0), self.mem_index[i]["meta"].get("ts", 0)))
        while len(self.mem_index) > self.cap:
            rm = order.pop(0)
            try:
                del self.mem_index[rm]
                del self.embeddings[rm]
            except Exception:
                pass
        # rewrite jsonl
        try:
            if self._encryption_enabled:
                text = "\n".join(json.dumps(it, ensure_ascii=False) for it in self.mem_index)
                enc = self._fernet.encrypt(text.encode("utf-8"))
                with open(MEMORY_JSONL_ENC, "wb") as f:
                    f.write(enc)
            else:
                with open(MEMORY_JSONL, "w", encoding="utf-8") as f:
                    for it in self.mem_index:
                        f.write(json.dumps(it, ensure_ascii=False) + "\n")
        except Exception as e:
            print("[Memory] Failed to rewrite JSONL after eviction:", e)

    def consolidate(self, keep_latest: int = 200, summarize_fn=None):
        """Summarize older memories into a consolidated memory to reduce token usage.

        keep_latest: number of newest memories to keep verbatim.
        summarize_fn: optional callable(texts->summary). If None, try to use Ollama/OpenAI.
        """
        if len(self.mem_index) <= keep_latest + 1:
            return
        old = self.mem_index[:-keep_latest]
        texts = [m["text"] for m in old]
        concat = "\n".join(texts)
        summary = None
        if summarize_fn:
            try:
                summary = summarize_fn(concat)
            except Exception:
                summary = None
        if not summary:
            # Try Ollama or OpenAI quickly
            try:
                import ollama
                resp = ollama.chat(model="llama3.2", messages=[{"role":"user","content": f"Summarize the following points briefly:\n{concat}"}])
                summary = resp.get("message", {}).get("content", "")
            except Exception:
                summary = concat[:1000]

        # create consolidated memory
        cons_id = str(uuid.uuid4())
        meta = {"ts": _now_ts(), "tags": ["consolidated"], "importance": 0.9, "source": "consolidation"}
        cons = {"id": cons_id, "text": summary, "meta": meta}
        # remove old
        self.mem_index = self.mem_index[-keep_latest:]
        self.embeddings = self._embed([m["text"] for m in self.mem_index])
        # append consolidated entry
        self.mem_index.insert(0, cons)
        self.embeddings.insert(0, self._embed([summary])[0])
        # rewrite jsonl
        try:
            if self._encryption_enabled:
                text = "\n".join(json.dumps(it, ensure_ascii=False) for it in self.mem_index)
                enc = self._fernet.encrypt(text.encode("utf-8"))
                with open(MEMORY_JSONL_ENC, "wb") as f:
                    f.write(enc)
            else:
                with open(MEMORY_JSONL, "w", encoding="utf-8") as f:
                    for it in self.mem_index:
                        f.write(json.dumps(it, ensure_ascii=False) + "\n")
        except Exception as e:
            print("[Memory] Failed to write JSONL after consolidation:", e)

    def list_memories(self, limit: int = 50) -> List[Dict]:
        return list(self.mem_index[-limit:])



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
        # LOAD MEMORY from disk if available, else start fresh with system prompt
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Basic integrity check: list with at least system prompt
                if isinstance(loaded, list) and loaded:
                    self.messages = loaded
                    print(f"   [Memory] Loaded {len(self.messages)} messages from {MEMORY_FILE}")
                else:
                    self.messages = [self.system_prompt]
            except Exception as e:
                print(f"[Memory] Failed to load {MEMORY_FILE}: {e}")
                self.messages = [self.system_prompt]
        else:
            self.messages = [self.system_prompt]

        # Try to import ollama; if not present we'll fall back to other backends
        try:
            import ollama

            self._ollama = ollama
        except Exception:
            self._ollama = None
        # Memory manager (RAG)
        try:
            self.memory = MemoryManager()
        except Exception as e:
            print("[Memory] Failed to init MemoryManager:", e)
            self.memory = None

    def think(self, user_text: str) -> str:
        """Return a short assistant response. Uses Ollama if available, else
        falls back to the module `process_command` logic for a quick reply.
        """
        # Quick memory commands handled locally
        _lt = user_text.strip()
        lt_low = _lt.lower()
        if lt_low.startswith("remember ") and self.memory:
            to_rem = _lt[len("remember "):].strip()
            mid = self.memory.add(to_rem, tags=["user_keep"], importance=0.8, source="user_command")
            return "Remembered." if mid else "Failed to remember."
        if lt_low.startswith("forget ") and self.memory:
            arg = _lt[len("forget "):].strip()
            # try to forget by id first, else by simple substring match
            ok = False
            if self.memory.forget(arg):
                ok = True
            else:
                # substring match
                for m in list(self.memory.mem_index):
                    if arg.lower() in m.get("text", "").lower():
                        ok = self.memory.forget(m.get("id")) or ok
            return "Forgotten." if ok else "Nothing matched to forget."
        if lt_low in ("show memories", "show memory", "list memories") and self.memory:
            items = self.memory.list_memories(limit=20)
            if not items:
                return "No memories stored."
            out = []
            for it in items:
                ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(it["meta"].get("ts", 0)))
                out.append(f"[{it['id'][:8]}] {ts} {it['text'][:120]}")
            return "\n".join(out)

        # Prefer Ollama for conversational replies
        if self._ollama:
            # Retrieve relevant long-term memories and inject into a temporary context
            retrieved = []
            try:
                if self.memory:
                    retrieved = self.memory.get_relevant(user_text, k=5)
            except Exception:
                retrieved = []

            temp_ctx = list(self.messages)
            if retrieved:
                # Build a concise system message listing top memories
                mem_lines = []
                for r in retrieved:
                    txt = r.get("text", "")
                    snippet = (txt[:300] + "...") if len(txt) > 300 else txt
                    mem_lines.append(f"- ({r.get('id')[:8]}) {snippet}")
                temp_ctx.append({"role": "system", "content": "Relevant memories:\n" + "\n".join(mem_lines)})

            temp_ctx.append({"role": "user", "content": user_text})
            try:
                resp = self._ollama.chat(model=self.model, messages=temp_ctx)
                reply = resp.get("message", {}).get("content", "")
                # Append to short-term conversation only
                self.messages.append({"role": "user", "content": user_text})
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
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, indent=2, ensure_ascii=False)
            print("Memory wiped and saved.")
        except Exception as e:
            print(f"[Memory] Failed to write cleared memory: {e}")
        # Also clear long-term memories if manager exists
        try:
            if getattr(self, "memory", None):
                self.memory.mem_index = []
                self.memory.embeddings = []
                if os.path.exists(MEMORY_JSONL):
                    try:
                        os.remove(MEMORY_JSONL)
                    except Exception:
                        pass
                print("Long-term memory cleared.")
        except Exception as _e:
            print(f"[Memory] Failed to clear long-term memory: {_e}")

    # Convenience APIs for long-term memory operations
    def remember(self, text: str, tags: Optional[List[str]] = None, importance: float = 0.6) -> str:
        if not getattr(self, "memory", None):
            raise RuntimeError("Memory manager not available")
        return self.memory.add(text, tags=tags or [], importance=importance, source="manual")

    def forget_memory(self, mid: str) -> bool:
        if not getattr(self, "memory", None):
            raise RuntimeError("Memory manager not available")
        return self.memory.forget(mid)

    def list_memories(self, limit: int = 50) -> List[Dict]:
        if not getattr(self, "memory", None):
            return []
        return self.memory.list_memories(limit=limit)

    def consolidate_memories(self, keep_latest: int = 200):
        if not getattr(self, "memory", None):
            raise RuntimeError("Memory manager not available")
        self.memory.consolidate(keep_latest=keep_latest)


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
