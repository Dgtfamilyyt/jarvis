import argparse
import threading
import queue
import time
from .core.listen import Listener
from .core.speak import Speaker
from .brain.llm_client import Brain
from .skills.system_ops import SystemSkills


def main(mode: str = "voice"):
    print("Initializing Jarvis Systems...")

    # Create modules. Use a larger model as requested.
    ear = None
    if mode in ("voice", "both"):
        ear = Listener(model_size="medium")

    mouth = Speaker()
    brain = Brain(model="llama3.2")  # Ensure Ollama is running
    skills = SystemSkills()

    mouth.speak_output("Systems online. Ready for commands.")

    # Shared queue for inputs discovered by any input worker
    input_q = queue.Queue()
    stop_event = threading.Event()

    def voice_worker():
        while not stop_event.is_set():
            try:
                text = ear.listen_input()
                if text:
                    input_q.put(("voice", text))
            except Exception as e:
                print("Voice worker error:", e)
                time.sleep(0.5)

    def text_worker():
        while not stop_event.is_set():
            try:
                u = input("You (text)> ").strip()
            except EOFError:
                stop_event.set()
                break
            except Exception as e:
                print("Text worker input error:", e)
                continue
            if u:
                input_q.put(("text", u))

    # Dispatcher consumes inputs and runs the routing logic
    def dispatcher():
        while not stop_event.is_set():
            try:
                mode_tag, user_input = input_q.get(timeout=0.5)
            except queue.Empty:
                continue

            user_input_lower = user_input.lower()
            print(f"User ({mode_tag}): {user_input}")

            # EXIT
            if "goodbye" in user_input_lower or "exit" in user_input_lower:
                mouth.speak_output("Shutting down. Goodbye.")
                stop_event.set()
                break

            # TIME
            if "time" in user_input_lower:
                response = skills.get_time()
                mouth.speak_output(response)
                continue

            # OPEN APPS
            if "open" in user_input_lower:
                app_name = user_input_lower.split("open ")[-1].strip()
                response = skills.launch_app(app_name)
                mouth.speak_output(response)
                continue

            # WEBSITES
            if "go to" in user_input_lower or "search for" in user_input_lower:
                url = user_input_lower.replace("go to", "").replace("search for", "").strip()
                response = skills.open_website(url)
                mouth.speak_output(response)
                continue

            # Brain fallback
            try:
                response = brain.think(user_input)
                mouth.speak_output(response)
            except Exception as e:
                print("Brain error:", e)
                mouth.speak_output("An error occurred while thinking.")

    # Start workers based on mode
    threads = []
    if mode in ("voice", "both") and ear is not None:
        t = threading.Thread(target=voice_worker, daemon=True)
        t.start()
        threads.append(t)

    if mode in ("text", "both"):
        t2 = threading.Thread(target=text_worker, daemon=True)
        t2.start()
        threads.append(t2)

    disp = threading.Thread(target=dispatcher, daemon=True)
    disp.start()
    threads.append(disp)

    try:
        # Wait until dispatcher finishes (stop_event set)
        while not stop_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        stop_event.set()

    # Join threads briefly
    for t in threads:
        t.join(timeout=1.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Jarvis in voice, text, or both modes")
    parser.add_argument("--mode", choices=["voice", "text", "both"], default="voice",
                        help="Input mode: 'voice' uses microphone, 'text' reads typed input, 'both' runs both concurrently.")
    parser.add_argument("--remember", type=str, help="Save text to long-term memory and exit")
    parser.add_argument("--forget", type=str, help="Forget memory by id or substring and exit")
    parser.add_argument("--list-memories", action="store_true", help="Print recent memories and exit")
    parser.add_argument("--consolidate", action="store_true", help="Consolidate older memories and exit")
    parser.add_argument("--keep", type=int, default=200, help="When consolidating, keep this many latest memories")
    args = parser.parse_args()

    # CLI memory operations: if any memory flag is present, perform the action and exit
    if args.remember or args.forget or args.list_memories or args.consolidate:
        # Initialize Brain (which will init MemoryManager if available)
        brain = Brain(model="llama3.2")

        if args.remember:
            try:
                mid = brain.remember(args.remember)
                print(f"Remembered id: {mid}")
            except Exception as e:
                print(f"Remember failed: {e}")
            exit(0)

        if args.forget:
            try:
                ok = brain.forget_memory(args.forget)
                print("Forgotten." if ok else "No matching memory found.")
            except Exception as e:
                print(f"Forget failed: {e}")
            exit(0)

        if args.list_memories:
            try:
                items = brain.list_memories(limit=200)
                if not items:
                    print("No memories stored.")
                else:
                    for it in items:
                        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(it["meta"].get("ts", 0)))
                        print(f"[{it['id'][:8]}] {ts} {it['text']}")
            except Exception as e:
                print(f"List memories failed: {e}")
            exit(0)

        if args.consolidate:
            try:
                brain.consolidate_memories(keep_latest=args.keep)
                print(f"Consolidated memories, kept {args.keep} latest.")
            except Exception as e:
                print(f"Consolidate failed: {e}")
            exit(0)

    main(mode=args.mode)
