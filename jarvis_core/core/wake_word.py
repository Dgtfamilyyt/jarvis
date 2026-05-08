def wait_for_wake_word(wake_word: str = "Jarvis"):
    """Very small demo: prompt user to type or press Enter to simulate wake-word detection."""
    try:
        text = input(f"Type the wake word ('{wake_word}') to continue (or press Enter to simulate): ")
        if not text or text.strip().lower() == wake_word.lower():
            return True
        return False
    except KeyboardInterrupt:
        return False
