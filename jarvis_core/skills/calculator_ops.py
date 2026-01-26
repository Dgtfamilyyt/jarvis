import re
from typing import Dict


class CalculatorSkills:
    def __init__(self):
        print("Calculator Skills loaded")

    def evaluate(self, expression: str) -> str:
        """Safely evaluate a math expression."""
        if not expression:
            return "No expression provided."
        
        try:
            # Only allow safe characters (digits, operators, parentheses, decimal point)
            if not re.match(r'^[0-9+\-*/().\s]+$', expression):
                return "Invalid characters in expression."
            
            result = eval(expression)
            return f"{expression} = {result}"
        except ZeroDivisionError:
            return "Cannot divide by zero."
        except Exception as e:
            return f"Calculation failed: {e}"

    def convert_units(self, value: float, from_unit: str, to_unit: str) -> str:
        """Convert between common units."""
        conversions = {
            ("km", "miles"): 0.621371,
            ("miles", "km"): 1.60934,
            ("kg", "lbs"): 2.20462,
            ("lbs", "kg"): 0.453592,
            ("c", "f"): lambda v: (v * 9/5) + 32,
            ("f", "c"): lambda v: (v - 32) * 5/9,
        }
        
        key = (from_unit.lower(), to_unit.lower())
        if key not in conversions:
            return f"Conversion from {from_unit} to {to_unit} not supported."
        
        try:
            factor = conversions[key]
            if callable(factor):
                result = factor(value)
            else:
                result = value * factor
            return f"{value} {from_unit} = {result:.2f} {to_unit}"
        except Exception as e:
            return f"Conversion failed: {e}"


_calculator_skills = CalculatorSkills()


def execute_function(payload: Dict):
    """Route calculator operations."""
    tool = payload.get("tool", "")
    
    if tool.endswith("evaluate") or tool.endswith("calculate"):
        expr = payload.get("expression") or payload.get("expr") or ""
        return _calculator_skills.evaluate(expr)
    
    if tool.endswith("convert"):
        value = payload.get("value", 0)
        from_unit = payload.get("from") or ""
        to_unit = payload.get("to") or ""
        return _calculator_skills.convert_units(value, from_unit, to_unit)
    
    return f"Unknown calculator tool: {tool}"
