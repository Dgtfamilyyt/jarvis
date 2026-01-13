import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jarvis_core.brain.llm_client as llm_mod
print('Memory smoke test starting')

from jarvis_core.brain.llm_client import MemoryManager

mm = MemoryManager(cap=100)
print('Backend SBERT available:', getattr(mm, '_sbert', None) is not None)
print('Backend OpenAI available:', getattr(mm, '_openai', None) is not None)

id1 = mm.add("Davin likes jazz music and late-night saxophone.", tags=['preference'], importance=0.6)
print('Added id1:', id1)
id2 = mm.add("Davin's favorite color is blue and he prefers ocean views.", tags=['preference'], importance=0.8)
print('Added id2:', id2)

print('\nQuery: "What is Davin\'s favorite color?"')
for m in mm.list_memories(limit=10):
    print(m.get('id')[:8], m.get('meta', {}).get('ts'), m.get('text')[:80])

res = mm.get_relevant("What is Davin's favorite color?", k=5)
print('Retrieved:')
for r in res:
    print(f"- id={r['id'][:8]} score={r['score']:.4f} text={r['text'][:80]}")

print('\nSmoke test complete')
