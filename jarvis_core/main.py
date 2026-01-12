from .core.listen import Listener
from .core.speak import Speaker
from .brain.llm_client import Brain
from .skills.system_ops import SystemSkills


def main():
    print("Initializing Jarvis Systems...")
    
    # 1. Initialize all modules
    ear = Listener(model_size="base") 
    mouth = Speaker()
    brain = Brain(model="llama3.2") # Ensure Ollama is running
    skills = SystemSkills()

    mouth.speak_output("Systems online. Ready for commands.")

    while True:
        try:
            # A. Listen
            user_input = ear.listen_input()
            if not user_input:
                continue

            user_input_lower = user_input.lower()
            print(f"User: {user_input}")

            # --- KEYWORD ROUTER (The "Reflexes") ---
            
            # EXIT
            if "goodbye" in user_input_lower or "exit" in user_input_lower:
                mouth.speak_output("Shutting down. Goodbye.")
                break

            # TIME
            elif "time" in user_input_lower:
                response = skills.get_time()
                mouth.speak_output(response)

            # OPEN APPS (e.g., "Open Calculator")
            elif "open" in user_input_lower:
                # Extract the app name (simple split logic)
                # "Open spotify" -> ["open", "spotify"] -> "spotify"
                app_name = user_input_lower.split("open ")[-1].strip()
                response = skills.launch_app(app_name)
                mouth.speak_output(response)

            # WEBSITES (e.g., "Go to youtube.com")
            elif "go to" in user_input_lower or "search for" in user_input_lower:
                 # "Go to google.com" -> "google.com"
                url = user_input_lower.replace("go to", "").replace("search for", "").strip()
                response = skills.open_website(url)
                mouth.speak_output(response)

            # --- THE BRAIN (Complex Queries) ---
            else:
                # If no simple command matched, ask the LLM
                response = brain.think(user_input)
                mouth.speak_output(response)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            mouth.speak_output("An error occurred.")


if __name__ == "__main__":
    main()
