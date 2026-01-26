import requests
from typing import Dict
import os
from dotenv import load_dotenv

load_dotenv()


class WeatherSkills:
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "")
        print("Weather Skills loaded")

    def get_weather(self, city: str) -> str:
        """Fetch current weather for a city using OpenWeatherMap API."""
        if not city:
            return "No city specified."
        
        if not self.api_key:
            return "OpenWeather API key not configured. Set OPENWEATHER_API_KEY in .env"
        
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                main = data.get("main", {})
                weather = data.get("weather", [{}])[0]
                temp = main.get("temp")
                desc = weather.get("description", "unknown")
                humidity = main.get("humidity")
                return f"Weather in {city}: {desc}, {temp}°C, humidity {humidity}%"
            else:
                return f"Could not find weather for {city}."
        except Exception as e:
            return f"Weather lookup failed: {e}"


_weather_skills = WeatherSkills()


def execute_function(payload: Dict):
    """Route weather operations."""
    tool = payload.get("tool", "")
    
    if tool.endswith("get_weather") or tool.endswith("weather"):
        city = payload.get("city") or payload.get("location") or ""
        return _weather_skills.get_weather(city)
    
    return f"Unknown weather tool: {tool}"
