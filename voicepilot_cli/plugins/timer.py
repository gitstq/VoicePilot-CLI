"""
Timer/Reminder plugin for VoicePilot-CLI.

Provides timer and reminder functionality with background execution.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from voicepilot_cli.plugins.base import PluginBase


class TimerPlugin(PluginBase):
    """Timer and reminder plugin.

    Supports setting timers, countdowns, and simple reminders.
    Timers run in background threads and print notifications when done.

    Configuration (in config.yaml):
        plugins.timer.notification_sound: Whether to play a sound (default: False)
        plugins.timer.default_duration: Default timer duration in seconds (default: 300)
    """

    # Unit to seconds conversion
    UNIT_CONVERSIONS: Dict[str, int] = {
        "秒": 1,
        "second": 1,
        "seconds": 1,
        "s": 1,
        "分钟": 60,
        "minute": 60,
        "minutes": 60,
        "min": 60,
        "小时": 3600,
        "hour": 3600,
        "hours": 3600,
        "hr": 3600,
        "h": 3600,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the timer plugin.

        Args:
            config: Optional configuration dictionary.
        """
        super().__init__(config)
        self._timers: Dict[str, Dict[str, Any]] = {}
        self._timer_counter = 0
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        """Get plugin name.

        Returns:
            'timer'
        """
        return "timer"

    @property
    def description(self) -> str:
        """Get plugin description.

        Returns:
            Description string.
        """
        return "Timer and reminder. Set countdowns and get notified."

    @property
    def trigger_keywords(self) -> List[str]:
        """Get trigger keywords.

        Returns:
            List of keywords that trigger this plugin.
        """
        return [
            "定时", "提醒", "闹钟", "计时", "倒计时", "计时器",
            "timer", "remind", "alarm", "countdown", "stopwatch",
            "分钟后", "小时后", "秒后", "分钟后叫我",
        ]

    @property
    def commands(self) -> List[str]:
        """Get supported commands.

        Returns:
            List of command strings.
        """
        return ["timer", "remind", "alarm", "countdown", "timers"]

    def execute(self, command: str, **kwargs: Any) -> str:
        """Execute a timer command.

        Args:
            command: Timer command string.
            **kwargs: Additional parameters (may include 'duration' and 'unit').

        Returns:
            Result string.
        """
        # Handle explicit parameters from planner
        if kwargs.get("duration") is not None:
            duration = int(kwargs["duration"])
            unit = kwargs.get("unit", "秒")
            return self._set_timer(duration, unit, command)

        # Handle subcommands
        command_lower = command.lower().strip()

        if command_lower in ("timers", "list", "列表"):
            return self._list_timers()
        elif command_lower in ("cancel", "取消", "stop", "停止"):
            return self._cancel_all_timers()
        elif command_lower.startswith("cancel ") or command_lower.startswith("取消 "):
            timer_id = command_lower.split(" ", 1)[1].strip()
            return self._cancel_timer(timer_id)

        # Parse natural language timer request
        return self._parse_and_set_timer(command)

    def _parse_and_set_timer(self, text: str) -> str:
        """Parse natural language and set a timer.

        Args:
            text: Natural language timer request.

        Returns:
            Result string or empty string if not a timer command.
        """
        import re

        # Try to match duration patterns
        patterns = [
            # "5分钟", "30秒", "2小时"
            r"(\d+)\s*(秒|分钟|小时|second|minute|hour|s|min|hr|h)",
            # "5分钟后提醒我", "30秒后"
            r"(\d+)\s*(秒|分钟|小时|second|minute|hour|s|min|hr|h)[^后]*后",
            # "timer 5 min", "countdown 30 seconds"
            r"(?:timer|countdown|alarm|remind)\s+(\d+)\s*(秒|分钟|小时|second|minute|hour|s|min|hr|h)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                duration = int(match.group(1))
                unit = match.group(2)
                return self._set_timer(duration, unit, text)

        return ""

    def _set_timer(self, duration: int, unit: str, label: str = "") -> str:
        """Set a new timer.

        Args:
            duration: Duration number.
            unit: Duration unit (秒, 分钟, 小时, etc.).
            label: Optional label/description for the timer.

        Returns:
            Confirmation message.
        """
        # Convert to seconds
        seconds = self._unit_to_seconds(duration, unit)

        if seconds <= 0:
            return "无效的定时时间"
        if seconds > 86400 * 7:  # Max 7 days
            return "定时时间过长，最长支持7天"

        with self._lock:
            self._timer_counter += 1
            timer_id = f"timer_{self._timer_counter}"

        # Calculate end time
        end_time = datetime.now() + timedelta(seconds=seconds)

        # Store timer info
        timer_info = {
            "id": timer_id,
            "duration": seconds,
            "unit": unit,
            "label": label or f"Timer {self._timer_counter}",
            "end_time": end_time.isoformat(),
            "active": True,
            "thread": None,
        }

        # Start timer in background thread
        timer_thread = threading.Thread(
            target=self._run_timer,
            args=(timer_id, seconds, label or f"Timer {self._timer_counter}"),
            daemon=True,
        )
        timer_info["thread"] = timer_thread
        self._timers[timer_id] = timer_info
        timer_thread.start()

        # Format duration for display
        duration_str = self._format_duration(seconds)

        return (
            f"⏰ 定时器已设置: {timer_info['label']}\n"
            f"   ID: {timer_id}\n"
            f"   时长: {duration_str}\n"
            f"   预计结束: {end_time.strftime('%H:%M:%S')}"
        )

    def _run_timer(self, timer_id: str, seconds: int, label: str) -> None:
        """Run a timer in the background.

        Args:
            timer_id: Unique timer identifier.
            seconds: Duration in seconds.
            label: Timer label for notification.
        """
        try:
            time.sleep(seconds)

            # Check if timer is still active
            with self._lock:
                timer = self._timers.get(timer_id)
                if timer is None or not timer.get("active", False):
                    return
                timer["active"] = False

            # Print notification
            duration_str = self._format_duration(seconds)
            notification = (
                f"\n🔔 定时器到期!\n"
                f"   {label}\n"
                f"   已过 {duration_str}\n"
                f"   时间: {datetime.now().strftime('%H:%M:%S')}\n"
            )
            print(notification)

            # Try to play notification sound
            if self.get_config("notification_sound", False):
                self._play_notification()

        except Exception as e:
            print(f"\n定时器错误 ({timer_id}): {e}")

    def _play_notification(self) -> None:
        """Play a notification sound."""
        try:
            import subprocess
            import platform

            system = platform.system()
            if system == "Linux":
                # Try to use paplay with a simple beep
                subprocess.run(
                    ["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"],
                    capture_output=True,
                    timeout=5,
                )
            elif system == "Darwin":
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"],
                             capture_output=True, timeout=5)
            elif system == "Windows":
                import winsound
                winsound.Beep(1000, 500)
        except Exception:
            pass  # Sound is optional

    def _cancel_timer(self, timer_id: str) -> str:
        """Cancel a specific timer.

        Args:
            timer_id: Timer identifier.

        Returns:
            Result message.
        """
        with self._lock:
            timer = self._timers.get(timer_id)
            if timer is None:
                return f"定时器不存在: {timer_id}"

            timer["active"] = False
            remaining = self._get_remaining_time(timer)
            return f"✅ 定时器 {timer_id} 已取消 (剩余: {self._format_duration(remaining)})"

    def _cancel_all_timers(self) -> str:
        """Cancel all active timers.

        Returns:
            Result message.
        """
        with self._lock:
            count = 0
            for timer_id, timer in self._timers.items():
                if timer.get("active", False):
                    timer["active"] = False
                    count += 1

        if count == 0:
            return "没有活跃的定时器"
        return f"✅ 已取消 {count} 个定时器"

    def _list_timers(self) -> str:
        """List all timers and their status.

        Returns:
            Formatted timer list.
        """
        with self._lock:
            if not self._timers:
                return "没有定时器"

            lines = [f"⏰ 定时器列表 ({len(self._timers)} 个):"]
            lines.append("─" * 50)

            for timer_id, timer in self._timers.items():
                status = "🟢 活跃" if timer.get("active", False) else "🔴 已完成/已取消"
                remaining = self._get_remaining_time(timer)
                duration_str = self._format_duration(timer["duration"])

                lines.append(
                    f"  {timer_id}: {timer['label']}\n"
                    f"    状态: {status} | 时长: {duration_str} | "
                    f"剩余: {self._format_duration(remaining)}"
                )

            return "\n".join(lines)

    def _get_remaining_time(self, timer: Dict[str, Any]) -> int:
        """Get remaining time for a timer.

        Args:
            timer: Timer info dictionary.

        Returns:
            Remaining seconds (0 if expired).
        """
        if not timer.get("active", False):
            return 0

        try:
            end_time = datetime.fromisoformat(timer["end_time"])
            remaining = (end_time - datetime.now()).total_seconds()
            return max(0, int(remaining))
        except (ValueError, KeyError):
            return 0

    def _unit_to_seconds(self, duration: int, unit: str) -> int:
        """Convert a duration with unit to seconds.

        Args:
            duration: Duration number.
            unit: Unit string.

        Returns:
            Duration in seconds.
        """
        unit_lower = unit.lower()
        return duration * self.UNIT_CONVERSIONS.get(unit_lower, duration)

    def _format_duration(self, seconds: int) -> str:
        """Format seconds into a human-readable duration string.

        Args:
            seconds: Duration in seconds.

        Returns:
            Formatted string (e.g., "1小时30分钟5秒").
        """
        if seconds <= 0:
            return "0秒"

        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分钟")
        if secs > 0 or not parts:
            parts.append(f"{secs}秒")

        return "".join(parts)

    def can_handle(self, input_text: str) -> bool:
        """Check if this plugin can handle the input.

        Args:
            input_text: User input text.

        Returns:
            True if the input is a timer/reminder request.
        """
        return super().can_handle(input_text)
