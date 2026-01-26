import json
from datetime import datetime, timedelta
from typing import Dict, List


class ReminderSkills:
    def __init__(self):
        self.reminders: List[Dict] = []
        print("Reminder Skills loaded")

    def set_reminder(self, text: str, minutes: int = 5) -> str:
        """Set a reminder for a specified number of minutes from now."""
        if not text:
            return "No reminder text specified."
        
        if minutes < 1:
            minutes = 5
        
        due_time = datetime.now() + timedelta(minutes=minutes)
        reminder = {
            "id": len(self.reminders) + 1,
            "text": text,
            "due": due_time.isoformat(),
            "done": False
        }
        self.reminders.append(reminder)
        return f"Reminder set: '{text}' in {minutes} minute(s)."

    def list_reminders(self) -> str:
        """List all pending reminders."""
        if not self.reminders:
            return "No reminders set."
        
        pending = [r for r in self.reminders if not r.get("done")]
        if not pending:
            return "No pending reminders."
        
        lines = []
        for r in pending:
            due = r.get("due", "unknown")
            lines.append(f"[{r['id']}] {r['text']} (due: {due})")
        
        return "\n".join(lines)

    def clear_reminder(self, reminder_id: int) -> str:
        """Mark a reminder as done."""
        for r in self.reminders:
            if r.get("id") == reminder_id:
                r["done"] = True
                return f"Reminder {reminder_id} cleared."
        
        return f"Reminder {reminder_id} not found."

    def clear_all_reminders(self) -> str:
        """Clear all reminders."""
        self.reminders = []
        return "All reminders cleared."


_reminder_skills = ReminderSkills()


def execute_function(payload: Dict):
    """Route reminder operations."""
    tool = payload.get("tool", "")
    
    if tool.endswith("set_reminder") or tool.endswith("remind"):
        text = payload.get("text") or payload.get("reminder") or ""
        minutes = payload.get("minutes") or payload.get("in_minutes") or 5
        try:
            minutes = int(minutes)
        except (ValueError, TypeError):
            minutes = 5
        return _reminder_skills.set_reminder(text, minutes)
    
    if tool.endswith("list_reminders") or tool.endswith("list"):
        return _reminder_skills.list_reminders()
    
    if tool.endswith("clear_reminder") or tool.endswith("clear"):
        reminder_id = payload.get("id") or payload.get("reminder_id")
        try:
            reminder_id = int(reminder_id)
        except (ValueError, TypeError):
            return "Invalid reminder ID."
        return _reminder_skills.clear_reminder(reminder_id)
    
    if tool.endswith("clear_all"):
        return _reminder_skills.clear_all_reminders()
    
    return f"Unknown reminder tool: {tool}"
