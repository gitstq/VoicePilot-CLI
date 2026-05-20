"""
Weather plugin for VoicePilot-CLI.

Provides weather information lookup capabilities.
Uses a mock implementation by default; can be extended
with real weather API integrations.
"""

import json
import os
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from datetime import datetime

from voicepilot_cli.plugins.base import PluginBase


class WeatherPlugin(PluginBase):
    """Weather information plugin.

    Provides weather queries for locations. By default, uses a mock
    implementation that returns simulated weather data. Can be
    configured to use real weather APIs (e.g., OpenWeatherMap).

    Configuration (in config.yaml):
        plugins.weather.api_key: API key for weather service
        plugins.weather.service: Weather service name ('mock', 'openweathermap')
        plugins.weather.units: Temperature units ('celsius', 'fahrenheit')
        plugins.weather.cache_ttl: Cache duration in seconds (default: 600)
    """

    # Default mock weather data for common locations
    MOCK_WEATHER: Dict[str, Dict[str, Any]] = {
        "北京": {
            "temperature": 22,
            "humidity": 45,
            "condition": "晴",
            "wind": "北风 3级",
            "feels_like": 20,
        },
        "上海": {
            "temperature": 25,
            "humidity": 65,
            "condition": "多云",
            "wind": "东南风 2级",
            "feels_like": 27,
        },
        "广州": {
            "temperature": 30,
            "humidity": 80,
            "condition": "阵雨",
            "wind": "南风 2级",
            "feels_like": 34,
        },
        "深圳": {
            "temperature": 29,
            "humidity": 75,
            "condition": "多云转晴",
            "wind": "西南风 3级",
            "feels_like": 32,
        },
        "成都": {
            "temperature": 20,
            "humidity": 70,
            "condition": "阴",
            "wind": "微风",
            "feels_like": 19,
        },
        "杭州": {
            "temperature": 24,
            "humidity": 60,
            "condition": "晴",
            "wind": "东风 2级",
            "feels_like": 23,
        },
        "beijing": {
            "temperature": 22,
            "humidity": 45,
            "condition": "Sunny",
            "wind": "North 3",
            "feels_like": 20,
        },
        "shanghai": {
            "temperature": 25,
            "humidity": 65,
            "condition": "Cloudy",
            "wind": "SE 2",
            "feels_like": 27,
        },
        "tokyo": {
            "temperature": 18,
            "humidity": 55,
            "condition": "Partly Cloudy",
            "wind": "E 2",
            "feels_like": 17,
        },
        "new york": {
            "temperature": 15,
            "humidity": 50,
            "condition": "Clear",
            "wind": "NW 3",
            "feels_like": 13,
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the weather plugin.

        Args:
            config: Optional configuration dictionary.
        """
        super().__init__(config)
        self._cache: Dict[str, tuple] = {}  # location -> (data, timestamp)
        self._cache_ttl = self.get_config("cache_ttl", 600)

    @property
    def name(self) -> str:
        """Get plugin name.

        Returns:
            'weather'
        """
        return "weather"

    @property
    def description(self) -> str:
        """Get plugin description.

        Returns:
            Description string.
        """
        return "Weather information lookup. Query current weather for any location."

    @property
    def trigger_keywords(self) -> List[str]:
        """Get trigger keywords.

        Returns:
            List of keywords that trigger this plugin.
        """
        return [
            "天气", "气温", "温度", "下雨", "刮风", "湿度",
            "weather", "temperature", "forecast", "rain",
            "几度", "冷不冷", "热不热",
        ]

    @property
    def commands(self) -> List[str]:
        """Get supported commands.

        Returns:
            List of command strings.
        """
        return ["weather", "forecast"]

    def execute(self, command: str, **kwargs: Any) -> str:
        """Execute a weather query.

        Args:
            command: Location name or weather query.
            **kwargs: Additional parameters (may include 'location').

        Returns:
            Weather information string.
        """
        location = kwargs.get("location", "")
        if location and location != "auto":
            return self._get_weather(location)

        # Extract location from command text
        location = self._extract_location(command)
        if location:
            return self._get_weather(location)

        return ""

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location name from query text.

        Args:
            text: Query text.

        Returns:
            Location name or None.
        """
        import re

        # Remove common prefixes
        text = re.sub(
            r"^(查|查看|查询|帮我查|what is|what's|how is|check)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s*(的?天气|气温|温度|weather|temperature|forecast)\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )

        location = text.strip()
        if location:
            return location
        return None

    def _get_weather(self, location: str) -> str:
        """Get weather information for a location.

        Checks cache first, then fetches fresh data.

        Args:
            location: Location name.

        Returns:
            Formatted weather information string.
        """
        # Check cache
        cache_key = location.lower()
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return self._format_weather(location, data)

        # Get fresh weather data
        data = self._fetch_weather(location)

        # Cache the result
        self._cache[cache_key] = (data, time.time())

        return self._format_weather(location, data)

    def _fetch_weather(self, location: str) -> Dict[str, Any]:
        """Fetch weather data for a location.

        Uses mock data by default. Can be extended to call real APIs.

        Args:
            location: Location name.

        Returns:
            Weather data dictionary.
        """
        # Check if we have mock data for this location
        location_lower = location.lower()
        for key, data in self.MOCK_WEATHER.items():
            if key.lower() == location_lower:
                # Add some variation based on time
                import random
                hour = datetime.now().hour
                temp_offset = random.randint(-2, 2)
                return {
                    **data,
                    "temperature": data["temperature"] + temp_offset,
                    "location": location,
                    "time": datetime.now().strftime("%H:%M"),
                }

        # Generate plausible mock data for unknown locations
        import random
        return {
            "location": location,
            "temperature": random.randint(10, 35),
            "humidity": random.randint(30, 90),
            "condition": random.choice(["晴", "多云", "阴", "小雨", "晴转多云"]),
            "wind": f"{random.choice(['北', '南', '东', '西', '东南', '西北'])}风 {random.randint(1, 5)}级",
            "feels_like": random.randint(8, 38),
            "time": datetime.now().strftime("%H:%M"),
        }

    def _format_weather(self, location: str, data: Dict[str, Any]) -> str:
        """Format weather data into a readable string.

        Args:
            location: Location name.
            data: Weather data dictionary.

        Returns:
            Formatted weather string.
        """
        lines = [
            f"📍 {data.get('location', location)} 天气",
            f"   🌡️ 温度: {data['temperature']}°C (体感 {data.get('feels_like', data['temperature'])}°C)",
            f"   🌤️ 状况: {data['condition']}",
            f"   💧 湿度: {data['humidity']}%",
            f"   🌬️ 风力: {data['wind']}",
        ]

        if data.get("time"):
            lines.append(f"   🕐 更新时间: {data['time']}")

        return "\n".join(lines)

    def can_handle(self, input_text: str) -> bool:
        """Check if this plugin can handle the input.

        Args:
            input_text: User input text.

        Returns:
            True if the input is a weather query.
        """
        return super().can_handle(input_text)
