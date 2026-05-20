"""
Conversation memory/history management for VoicePilot-CLI.

Manages conversation history with configurable max length, persistence,
and context window management.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Message:
    """Represents a single conversation message.

    Attributes:
        role: Message role ('system', 'user', 'assistant', 'tool').
        content: Message content string.
        timestamp: When the message was created.
        metadata: Optional additional metadata (token count, plugin used, etc.).
    """

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize a message.

        Args:
            role: Message role ('system', 'user', 'assistant', 'tool').
            content: Message content string.
            timestamp: ISO format timestamp string. Defaults to now.
            metadata: Optional metadata dictionary.
        """
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary.

        Returns:
            Dictionary representation of the message.
        """
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Deserialize a message from dictionary.

        Args:
            data: Dictionary with message data.

        Returns:
            Message instance.
        """
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return f"Message(role={self.role!r}, content={self.content!r}[:50])"


class ConversationMemory:
    """Manages conversation history with configurable limits and persistence.

    Handles storing, retrieving, and managing the conversation context
    for the AI agent. Supports automatic trimming to stay within
    configured limits and optional file-based persistence.

    Attributes:
        max_history: Maximum number of messages to keep.
        messages: List of conversation messages.
    """

    def __init__(
        self,
        max_history: int = 50,
        history_file: Optional[str] = None,
        auto_save: bool = True,
    ) -> None:
        """Initialize conversation memory.

        Args:
            max_history: Maximum number of messages to retain.
            history_file: Optional path to persist conversation history.
            auto_save: Whether to automatically save after each message.
        """
        self.max_history = max_history
        self.history_file = Path(os.path.expanduser(history_file)) if history_file else None
        self.auto_save = auto_save
        self._messages: List[Message] = []
        self._system_prompt: Optional[str] = None

        if self.history_file:
            self._load()

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt for the conversation.

        Args:
            prompt: System prompt string.
        """
        self._system_prompt = prompt

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Add a message to the conversation history.

        Args:
            role: Message role ('system', 'user', 'assistant', 'tool').
            content: Message content.
            metadata: Optional metadata.

        Returns:
            The created Message instance.
        """
        message = Message(role=role, content=content, metadata=metadata or {})
        self._messages.append(message)
        self._trim()
        if self.auto_save:
            self._save()
        return message

    def add_user_message(self, content: str) -> Message:
        """Add a user message.

        Args:
            content: User message content.

        Returns:
            The created Message instance.
        """
        return self.add_message("user", content)

    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Add an assistant message.

        Args:
            content: Assistant message content.
            metadata: Optional metadata.

        Returns:
            The created Message instance.
        """
        return self.add_message("assistant", content, metadata=metadata)

    def add_tool_message(self, content: str, tool_name: str = "") -> Message:
        """Add a tool/plugin response message.

        Args:
            content: Tool response content.
            tool_name: Name of the tool/plugin that generated the response.

        Returns:
            The created Message instance.
        """
        return self.add_message("tool", content, metadata={"tool": tool_name})

    def get_context(self, max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """Get the conversation context for LLM input.

        Returns messages in the format expected by LLM APIs:
        [{"role": "...", "content": "..."}, ...]

        Args:
            max_tokens: Optional max token estimate for context window.
                       If provided, trims older messages to fit.

        Returns:
            List of message dictionaries for LLM API.
        """
        context: List[Dict[str, str]] = []

        # Add system prompt first
        if self._system_prompt:
            context.append({"role": "system", "content": self._system_prompt})

        # Add conversation messages
        messages = list(self._messages)

        # If max_tokens is specified, trim from the beginning
        if max_tokens is not None:
            messages = self._trim_for_tokens(messages, max_tokens)

        for msg in messages:
            context.append({"role": msg.role, "content": msg.content})

        return context

    def _trim_for_tokens(self, messages: List[Message], max_tokens: int) -> List[Message]:
        """Trim messages to fit within a token budget.

        Uses a simple character-based heuristic: ~4 chars per token.
        Keeps the most recent messages that fit within the budget.

        Args:
            messages: List of messages to trim.
            max_tokens: Maximum token budget.

        Returns:
            Trimmed list of messages.
        """
        max_chars = max_tokens * 4  # Rough estimate
        total_chars = 0
        result: List[Message] = []

        # Work backwards to keep most recent messages
        for msg in reversed(messages):
            msg_chars = len(msg.content)
            if total_chars + msg_chars > max_chars and result:
                break
            result.append(msg)
            total_chars += msg_chars

        result.reverse()
        return result

    def _trim(self) -> None:
        """Trim messages to stay within max_history limit."""
        if len(self._messages) > self.max_history:
            self._messages = self._messages[-self.max_history:]

    def clear(self) -> None:
        """Clear all conversation history (except system prompt)."""
        self._messages.clear()
        if self.auto_save:
            self._save()

    @property
    def message_count(self) -> int:
        """Get the number of messages in history.

        Returns:
            Message count.
        """
        return len(self._messages)

    @property
    def messages(self) -> List[Message]:
        """Get a copy of all messages.

        Returns:
            List of Message instances.
        """
        return list(self._messages)

    def get_last_exchange(self) -> Optional[Tuple[Message, Optional[Message]]]:
        """Get the most recent user-assistant exchange.

        Returns:
            Tuple of (user_message, assistant_message) or None.
        """
        if not self._messages:
            return None

        last_msg = self._messages[-1]
        if last_msg.role == "assistant" and len(self._messages) >= 2:
            return (self._messages[-2], last_msg)
        elif last_msg.role == "user":
            return (last_msg, None)
        return None

    def search(self, query: str, limit: int = 5) -> List[Message]:
        """Search conversation history for messages containing a query.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of matching messages.
        """
        query_lower = query.lower()
        results = [
            msg for msg in self._messages
            if query_lower in msg.content.lower()
        ]
        return results[-limit:]

    def _save(self) -> None:
        """Save conversation history to file."""
        if not self.history_file:
            return

        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "system_prompt": self._system_prompt,
                "messages": [msg.to_dict() for msg in self._messages],
            }
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (IOError, OSError) as e:
            import sys
            print(f"Warning: Could not save history: {e}", file=sys.stderr)

    def _load(self) -> None:
        """Load conversation history from file."""
        if not self.history_file or not self.history_file.exists():
            return

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._system_prompt = data.get("system_prompt")
            self._messages = [
                Message.from_dict(msg) for msg in data.get("messages", [])
            ]
        except (json.JSONDecodeError, IOError, KeyError) as e:
            import sys
            print(f"Warning: Could not load history: {e}", file=sys.stderr)
            self._messages = []

    def export(self, filepath: str) -> None:
        """Export conversation history to a file.

        Args:
            filepath: Path to export file.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "exported_at": datetime.now().isoformat(),
            "system_prompt": self._system_prompt,
            "message_count": len(self._messages),
            "messages": [msg.to_dict() for msg in self._messages],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def __len__(self) -> int:
        return len(self._messages)

    def __repr__(self) -> str:
        return f"ConversationMemory(messages={len(self._messages)}, max={self.max_history})"
