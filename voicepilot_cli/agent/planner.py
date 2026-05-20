"""
Task planning and decomposition for VoicePilot-CLI.

Provides intelligent task analysis, decomposition into subtasks,
and execution planning for complex user requests.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TaskPriority(Enum):
    """Priority levels for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubTask:
    """Represents a subtask within a plan.

    Attributes:
        description: Description of the subtask.
        action: The action to perform (e.g., 'calculate', 'search', 'respond').
        parameters: Parameters for the action.
        status: Current status of the subtask.
        result: Result of executing the subtask.
        depends_on: Indices of subtasks this depends on.
    """
    description: str
    action: str = "respond"
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    depends_on: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert subtask to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "description": self.description,
            "action": self.action,
            "parameters": self.parameters,
            "status": self.status.value,
            "result": self.result,
            "depends_on": self.depends_on,
        }


@dataclass
class TaskPlan:
    """A plan consisting of multiple subtasks.

    Attributes:
        goal: The overall goal of the plan.
        subtasks: List of subtasks to execute.
        current_index: Index of the currently executing subtask.
    """
    goal: str
    subtasks: List[SubTask] = field(default_factory=list)
    current_index: int = 0

    @property
    def is_complete(self) -> bool:
        """Check if all subtasks are completed.

        Returns:
            True if all subtasks are done.
        """
        return all(
            st.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)
            for st in self.subtasks
        )

    @property
    def current_subtask(self) -> Optional[SubTask]:
        """Get the current subtask to execute.

        Returns:
            Current SubTask or None if plan is complete.
        """
        if self.current_index < len(self.subtasks):
            return self.subtasks[self.current_index]
        return None

    def advance(self) -> bool:
        """Advance to the next subtask.

        Returns:
            True if there is a next subtask, False if plan is complete.
        """
        self.current_index += 1
        return self.current_index < len(self.subtasks)

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "goal": self.goal,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "current_index": self.current_index,
            "is_complete": self.is_complete,
        }


class TaskPlanner:
    """Analyzes user input and creates execution plans.

    Decomposes complex requests into actionable subtasks,
    identifies which plugins or tools are needed, and
    creates an execution plan.

    The planner uses pattern matching and keyword analysis
    to determine the intent and required actions without
    requiring an LLM call for planning itself.
    """

    # Pattern definitions for intent recognition
    INTENT_PATTERNS: Dict[str, List[str]] = {
        "calculate": [
            r"计算", r"算", r"多少", r"\d+\s*[\+\-\*\/\%\^]\s*\d+",
            r"calculate", r"compute", r"what is \d+",
            r"加|减|乘|除", r"等于",
        ],
        "weather": [
            r"天气", r"气温", r"温度", r"下雨",
            r"weather", r"temperature", r"forecast",
        ],
        "file_read": [
            r"读取.*文件", r"打开.*文件", r"查看.*文件", r"读.*文件",
            r"read.*file", r"open.*file", r"cat ",
        ],
        "file_write": [
            r"写入.*文件", r"保存.*文件", r"创建.*文件",
            r"write.*file", r"save.*file", r"create.*file",
        ],
        "file_list": [
            r"列出.*文件", r"查看.*目录", r"文件列表",
            r"list.*file", r"ls ", r"dir ",
        ],
        "timer": [
            r"定时", r"提醒", r"闹钟", r"计时", r"倒计时",
            r"timer", r"remind", r"alarm", r"countdown",
            r"\d+\s*(秒|分|小时|分钟|seconds?|minutes?|hours?)",
        ],
        "search": [
            r"搜索", r"查找", r"搜一下",
            r"search", r"find", r"look up",
        ],
        "greeting": [
            r"^(你好|hi|hello|hey|嗨|早上好|晚上好|下午好)",
        ],
        "farewell": [
            r"^(再见|拜拜|bye|goodbye|晚安|下次见)",
        ],
        "thanks": [
            r"^(谢谢|感谢|thanks|thank you|thx)",
        ],
    }

    def __init__(self) -> None:
        """Initialize the task planner with compiled patterns."""
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            self._compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def analyze_intent(self, user_input: str) -> Tuple[str, float]:
        """Analyze user input to determine the primary intent.

        Args:
            user_input: The user's input text.

        Returns:
            Tuple of (intent_name, confidence_score).
        """
        scores: Dict[str, int] = {}

        for intent, patterns in self._compiled_patterns.items():
            match_count = sum(1 for p in patterns if p.search(user_input))
            if match_count > 0:
                scores[intent] = match_count

        if not scores:
            return ("general", 0.5)

        best_intent = max(scores, key=scores.get)  # type: ignore
        confidence = min(scores[best_intent] / 3.0, 1.0)  # type: ignore
        return (best_intent, confidence)

    def create_plan(self, user_input: str) -> TaskPlan:
        """Create an execution plan for the user's request.

        Analyzes the input, determines intent, and creates
        a plan with appropriate subtasks.

        Args:
            user_input: The user's input text.

        Returns:
            A TaskPlan with subtasks to execute.
        """
        intent, confidence = self.analyze_intent(user_input)

        plan = TaskPlan(goal=user_input)

        if intent == "calculate":
            plan.subtasks = self._create_calculation_plan(user_input)
        elif intent == "weather":
            plan.subtasks = self._create_weather_plan(user_input)
        elif intent in ("file_read", "file_write", "file_list"):
            plan.subtasks = self._create_file_plan(intent, user_input)
        elif intent == "timer":
            plan.subtasks = self._create_timer_plan(user_input)
        elif intent == "greeting":
            plan.subtasks = [
                SubTask(
                    description="Respond to greeting",
                    action="respond",
                    parameters={"type": "greeting"},
                )
            ]
        elif intent == "farewell":
            plan.subtasks = [
                SubTask(
                    description="Respond to farewell",
                    action="respond",
                    parameters={"type": "farewell"},
                )
            ]
        elif intent == "thanks":
            plan.subtasks = [
                SubTask(
                    description="Acknowledge thanks",
                    action="respond",
                    parameters={"type": "acknowledge"},
                )
            ]
        else:
            # General query - just respond
            plan.subtasks = [
                SubTask(
                    description=f"Respond to: {user_input[:100]}",
                    action="respond",
                    parameters={"type": "general"},
                )
            ]

        return plan

    def _create_calculation_plan(self, user_input: str) -> List[SubTask]:
        """Create a plan for calculation tasks.

        Args:
            user_input: User's calculation request.

        Returns:
            List of subtasks.
        """
        # Try to extract the mathematical expression
        expression = self._extract_expression(user_input)

        return [
            SubTask(
                description=f"Calculate: {expression or user_input}",
                action="calculate",
                parameters={"expression": expression or user_input},
            ),
            SubTask(
                description="Format and present the result",
                action="respond",
                parameters={"type": "calculation_result"},
                depends_on=[0],
            ),
        ]

    def _create_weather_plan(self, user_input: str) -> List[SubTask]:
        """Create a plan for weather query tasks.

        Args:
            user_input: User's weather query.

        Returns:
            List of subtasks.
        """
        location = self._extract_location(user_input)

        return [
            SubTask(
                description=f"Get weather for: {location or 'current location'}",
                action="weather",
                parameters={"location": location or "auto"},
            ),
            SubTask(
                description="Present weather information",
                action="respond",
                parameters={"type": "weather_result"},
                depends_on=[0],
            ),
        ]

    def _create_file_plan(self, intent: str, user_input: str) -> List[SubTask]:
        """Create a plan for file operation tasks.

        Args:
            intent: Specific file intent (file_read, file_write, file_list).
            user_input: User's file operation request.

        Returns:
            List of subtasks.
        """
        filepath = self._extract_filepath(user_input)

        if intent == "file_read":
            return [
                SubTask(
                    description=f"Read file: {filepath or 'specified file'}",
                    action="file_read",
                    parameters={"path": filepath or ""},
                ),
                SubTask(
                    description="Present file contents",
                    action="respond",
                    parameters={"type": "file_content"},
                    depends_on=[0],
                ),
            ]
        elif intent == "file_write":
            return [
                SubTask(
                    description=f"Write to file: {filepath or 'specified file'}",
                    action="file_write",
                    parameters={"path": filepath or "", "content": user_input},
                ),
            ]
        else:  # file_list
            return [
                SubTask(
                    description=f"List files in: {filepath or 'current directory'}",
                    action="file_list",
                    parameters={"path": filepath or "."},
                ),
            ]

    def _create_timer_plan(self, user_input: str) -> List[SubTask]:
        """Create a plan for timer/reminder tasks.

        Args:
            user_input: User's timer request.

        Returns:
            List of subtasks.
        """
        duration, unit = self._extract_timer_duration(user_input)

        return [
            SubTask(
                description=f"Set timer for {duration} {unit}",
                action="timer",
                parameters={"duration": duration, "unit": unit},
            ),
            SubTask(
                description="Confirm timer has been set",
                action="respond",
                parameters={"type": "timer_confirmation"},
                depends_on=[0],
            ),
        ]

    def _extract_expression(self, text: str) -> Optional[str]:
        """Extract a mathematical expression from text.

        Args:
            text: Input text containing a math expression.

        Returns:
            Extracted expression string or None.
        """
        # Match common math patterns
        patterns = [
            r"[\d\.\,]+[\s]*[\+\-\*\/\%\^][\s]*[\d\.\,]+(?:[\s]*[\+\-\*\/\%\^][\s]*[\d\.\,]+)*",
            r"\([\d\.\,]+[\s]*[\+\-\*\/\%\^][\s]*[\d\.\,]+\)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()
        return None

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract a location name from text.

        Args:
            text: Input text possibly containing a location.

        Returns:
            Extracted location string or None.
        """
        # Common patterns for location extraction
        patterns = [
            r"(?:在|的|去|到)([\u4e00-\u9fff]{2,10})(?:天气|气温)",
            r"([\u4e00-\u9fff]{2,10})(?:天气|气温|温度)",
            r"(?:weather|temperature|forecast)\s+(?:in|for|at)\s+(\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_filepath(self, text: str) -> Optional[str]:
        """Extract a file path from text.

        Args:
            text: Input text possibly containing a file path.

        Returns:
            Extracted file path string or None.
        """
        # Match quoted paths or paths with common prefixes
        patterns = [
            r"['\"]([^'\"]+\.\w+)['\"]",
            r"([\w\-\.\/\\]+\.\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_timer_duration(self, text: str) -> Tuple[Optional[int], str]:
        """Extract timer duration and unit from text.

        Args:
            text: Input text containing a duration.

        Returns:
            Tuple of (duration_number, unit_string).
        """
        patterns = [
            (r"(\d+)\s*(秒|second)", "秒"),
            (r"(\d+)\s*(分钟|minute|min)", "分钟"),
            (r"(\d+)\s*(小时|hour|hr)", "小时"),
        ]
        for pattern, unit in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return (int(match.group(1)), unit)
        return (None, "秒")
