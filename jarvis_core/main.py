import argparse
import threading
import queue
import time
from typing import Optional
from .core.listen import Listener
from .core.speak import Speaker
from .brain.llm_client import Brain
from .skills.system_ops import SystemSkills
from . import config


def main(mode: str = "voice", offline: bool = False, wakeword_enabled: Optional[bool] = None):
    print("Initializing Jarvis Systems...", flush=True)

    # Determine wakeword setting (CLI override beats env)
    if wakeword_enabled is None:
        wake_enabled = config.WAKEWORD_ENABLED
    else:
        wake_enabled = bool(wakeword_enabled)

    # Create modules. Use a larger model as requested.
    ear = None
    if mode in ("voice", "both"):
        ear = Listener(model_size="large")

    mouth = Speaker(offline=offline)
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
                if not text:
                    continue
                text_lower = text.lower()

                # If wakeword enabled, only accept commands that include the wake word
                if wake_enabled:
                    if config.WAKE_WORD.lower() in text_lower:
                        # strip wake word from the captured phrase
                        idx = text_lower.find(config.WAKE_WORD.lower())
                        remainder = text[idx + len(config.WAKE_WORD):].strip()
                        if remainder:
                            print(f"[VOICE] Wakeword + command: {remainder}", flush=True)
                            input_q.put(("voice", remainder))
                        else:
                            # Wakeword only: prompt for follow-up
                            print(f"[VOICE] Wakeword detected, prompting for command", flush=True)
                            mouth.speak_output("Yes?")
                            follow = ear.listen_input()
                            if follow:
                                print(f"[VOICE] Follow-up after wakeword: {follow}", flush=True)
                                input_q.put(("voice", follow))
                    else:
                        print(f"[VOICE] (ignored - no wakeword) Heard: {text}", flush=True)
                else:
                    print(f"[VOICE] Heard: {text}", flush=True)
                    input_q.put(("voice", text))
            except Exception as e:
                print(f"[VOICE] Voice worker error: {e}", flush=True)
                time.sleep(0.5)

    def text_worker():
        while not stop_event.is_set():
            try:
                u = input("You (text)> ").strip()
            except EOFError:
                stop_event.set()
                break
            except Exception as e:
                print(f"[TEXT] Text worker input error: {e}", flush=True)
                continue
            if u:
                print(f"[TEXT] Text input accepted: {u}", flush=True)
                input_q.put(("text", u))

    # Dispatcher consumes inputs and runs the routing logic
    def dispatcher():
        while not stop_event.is_set():
            try:
                mode_tag, user_input = input_q.get(timeout=0.5)
            except queue.Empty:
                continue

            user_input_lower = user_input.lower()
            print(f"[DISPATCHER] User ({mode_tag}): {user_input}", flush=True)

            # EXIT
            if "goodbye" in user_input_lower or "exit" in user_input_lower:
                print(f"[DISPATCHER] Exit command detected", flush=True)
                mouth.speak_output("Shutting down. Goodbye.")
                stop_event.set()
                break

            # TIME
            if "time" in user_input_lower:
                print(f"[DISPATCHER] Time command detected", flush=True)
                response = skills.get_time()
                print(f"[DISPATCHER] Time response: {response}", flush=True)
                mouth.speak_output(response)
                continue

            # OPEN APPS
            if "open" in user_input_lower:
                print(f"[DISPATCHER] Open app command detected", flush=True)
                app_name = user_input_lower.split("open ")[-1].strip()
                response = skills.launch_app(app_name)
                print(f"[DISPATCHER] App launch response: {response}", flush=True)
                mouth.speak_output(response)
                continue

            # WEBSITES
            if "go to" in user_input_lower or "search for" in user_input_lower:
                print(f"[DISPATCHER] Website command detected", flush=True)
                url = user_input_lower.replace("go to", "").replace("search for", "").strip()
                response = skills.open_website(url)
                print(f"[DISPATCHER] Website response: {response}", flush=True)
                mouth.speak_output(response)
                continue

            # Brain fallback
            try:
                print(f"[DISPATCHER] Routing to Brain for response...", flush=True)
                response = brain.think(user_input)
                print(f"[DISPATCHER] Brain response: {response}", flush=True)
                mouth.speak_output(response)
            except Exception as e:
                print(f"[DISPATCHER] Brain error: {e}", flush=True)
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
    parser.add_argument("--offline", action="store_true", help="Use offline-only TTS (pyttsx3); skip ElevenLabs and edge-tts.")
    parser.add_argument("--no-wakeword", action="store_true", help="Disable wakeword detection and accept any speech as command.")
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

    wakeflag = not args.no_wakeword
    main(mode=args.mode, offline=args.offline, wakeword_enabled=wakeflag)
