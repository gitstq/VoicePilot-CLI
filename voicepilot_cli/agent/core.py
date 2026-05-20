"""
Agent core - conversation loop and context management for VoicePilot-CLI.

This is the central module that orchestrates all components:
- LLM communication
- Voice I/O (STT/TTS)
- Plugin execution
- Memory management
- Task planning
"""

import sys
import time
from typing import Any, Dict, Generator, List, Optional, Tuple

from voicepilot_cli.config import VoicePilotConfig
from voicepilot_cli.agent.memory import ConversationMemory
from voicepilot_cli.agent.planner import TaskPlanner, TaskPlan
from voicepilot_cli.utils.logger import get_logger


class AgentCore:
    """Core agent that manages the conversation loop.

    Orchestrates LLM calls, voice I/O, plugin execution, and
    memory management. Supports both text-only and voice modes.

    Attributes:
        config: VoicePilotConfig instance.
        memory: ConversationMemory instance.
        planner: TaskPlanner instance.
        logger: Logger instance.
    """

    def __init__(self, config: Optional[VoicePilotConfig] = None) -> None:
        """Initialize the agent core.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or VoicePilotConfig()
        self.logger = get_logger("agent")

        # Initialize memory
        history_file = self.config.get("agent.history_file")
        self.memory = ConversationMemory(
            max_history=self.config.max_history,
            history_file=history_file,
            auto_save=self.config.get("agent.auto_save_history", True),
        )
        self.memory.set_system_prompt(self.config.system_prompt)

        # Initialize planner
        self.planner = TaskPlanner()

        # Initialize LLM backend (lazy loaded)
        self._llm = None

        # Initialize voice backends (lazy loaded)
        self._stt = None
        self._tts = None

        # Initialize plugin registry (lazy loaded)
        self._plugin_registry = None

        # Track active timers
        self._active_timers: Dict[str, Dict[str, Any]] = {}

    @property
    def llm(self):
        """Get or initialize the LLM backend.

        Returns:
            LLM backend instance.

        Raises:
            RuntimeError: If no LLM backend is available.
        """
        if self._llm is None:
            self._llm = self._init_llm_backend()
        return self._llm

    @property
    def stt(self):
        """Get or initialize the STT backend.

        Returns:
            STT backend instance or None if not available.
        """
        if self._stt is None:
            self._stt = self._init_stt_backend()
        return self._stt

    @property
    def tts(self):
        """Get or initialize the TTS backend.

        Returns:
            TTS backend instance or None if not available.
        """
        if self._tts is None:
            self._tts = self._init_tts_backend()
        return self._tts

    @property
    def plugin_registry(self):
        """Get or initialize the plugin registry.

        Returns:
            PluginRegistry instance.
        """
        if self._plugin_registry is None:
            from voicepilot_cli.plugins.registry import PluginRegistry
            self._plugin_registry = PluginRegistry(config=self.config)
        return self._plugin_registry

    def _init_llm_backend(self):
        """Initialize the LLM backend based on configuration.

        Tries to load the configured backend, falls back to
        available backends if the primary is not available.

        Returns:
            LLM backend instance.

        Raises:
            RuntimeError: If no LLM backend can be initialized.
        """
        backend_name = self.config.llm_backend
        self.logger.info(f"Initializing LLM backend: {backend_name}")

        # Try the configured backend first
        backend = self._try_load_llm_backend(backend_name)
        if backend:
            return backend

        # Fall back to other available backends
        fallbacks = ["ollama", "openai", "glm"]
        for fb in fallbacks:
            if fb != backend_name:
                backend = self._try_load_llm_backend(fb)
                if backend:
                    self.logger.info(f"Falling back to LLM backend: {fb}")
                    self.config.set("llm.backend", fb)
                    return backend

        raise RuntimeError(
            "No LLM backend available. Please install one of: "
            "openai (pip install openai), "
            "ollama (pip install ollama), "
            "or glm (pip install zhipuai)"
        )

    def _try_load_llm_backend(self, name: str):
        """Try to load a specific LLM backend.

        Args:
            name: Backend name ('openai', 'ollama', 'glm').

        Returns:
            LLM backend instance or None if not available.
        """
        try:
            if name == "openai":
                from voicepilot_cli.llm.openai_backend import OpenAIBackend
                backend_config = self.config.get_backend_config("openai")
                return OpenAIBackend(
                    api_key=backend_config.get("api_key", ""),
                    base_url=backend_config.get("base_url", ""),
                    model=self.config.llm_model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
            elif name == "ollama":
                from voicepilot_cli.llm.ollama_backend import OllamaBackend
                backend_config = self.config.get_backend_config("ollama")
                return OllamaBackend(
                    base_url=backend_config.get("base_url", "http://localhost:11434"),
                    model=self.config.llm_model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
            elif name == "glm":
                from voicepilot_cli.llm.glm_backend import GLMBackend
                backend_config = self.config.get_backend_config("glm")
                return GLMBackend(
                    api_key=backend_config.get("api_key", ""),
                    model=self.config.llm_model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
        except ImportError:
            self.logger.debug(f"LLM backend '{name}' not installed")
        except Exception as e:
            self.logger.warning(f"Failed to initialize LLM backend '{name}': {e}")
        return None

    def _init_stt_backend(self):
        """Initialize the STT (Speech-to-Text) backend.

        Returns:
            STT backend instance or None if not available.
        """
        backend_name = self.config.stt_backend
        self.logger.info(f"Initializing STT backend: {backend_name}")

        try:
            from voicepilot_cli.voice.stt import STTEngine
            return STTEngine(backend=backend_name, config=self.config)
        except Exception as e:
            self.logger.warning(f"Failed to initialize STT backend: {e}")
            return None

    def _init_tts_backend(self):
        """Initialize the TTS (Text-to-Speech) backend.

        Returns:
            TTS backend instance or None if not available.
        """
        backend_name = self.config.tts_backend
        self.logger.info(f"Initializing TTS backend: {backend_name}")

        try:
            from voicepilot_cli.voice.tts import TTSEngine
            return TTSEngine(backend=backend_name, config=self.config)
        except Exception as e:
            self.logger.warning(f"Failed to initialize TTS backend: {e}")
            return None

    def process_input(self, user_input: str) -> str:
        """Process a user input and generate a response.

        This is the main processing pipeline:
        1. Check if any plugin can handle the request
        2. If not, create a task plan
        3. Execute the plan (may involve LLM calls)
        4. Return the response

        Args:
            user_input: User's text input.

        Returns:
            Agent's response string.
        """
        self.logger.info(f"Processing input: {user_input[:100]}")

        # Add user message to memory
        self.memory.add_user_message(user_input)

        # Try plugin execution first
        plugin_result = self._try_plugin_execution(user_input)
        if plugin_result:
            self.memory.add_assistant_message(plugin_result, metadata={"source": "plugin"})
            return plugin_result

        # Create and execute task plan
        plan = self.planner.create_plan(user_input)
        response = self._execute_plan(plan)

        # Add response to memory
        self.memory.add_assistant_message(response)

        return response

    def process_input_stream(self, user_input: str) -> Generator[str, None, None]:
        """Process user input and yield streaming response chunks.

        Args:
            user_input: User's text input.

        Yields:
            Response text chunks as they are generated.
        """
        self.logger.info(f"Processing streaming input: {user_input[:100]}")

        # Add user message to memory
        self.memory.add_user_message(user_input)

        # Try plugin execution first (plugins don't stream)
        plugin_result = self._try_plugin_execution(user_input)
        if plugin_result:
            self.memory.add_assistant_message(plugin_result, metadata={"source": "plugin"})
            yield plugin_result
            return

        # Stream from LLM
        context = self.memory.get_context()
        full_response = ""

        try:
            for chunk in self.llm.stream(context):
                full_response += chunk
                yield chunk
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            full_response = f"Error generating response: {e}"
            yield full_response

        self.memory.add_assistant_message(full_response)

    def _try_plugin_execution(self, user_input: str) -> Optional[str]:
        """Try to execute the input through a matching plugin.

        Args:
            user_input: User's input text.

        Returns:
            Plugin result string or None if no plugin matched.
        """
        try:
            registry = self.plugin_registry
            result = registry.execute_matching(user_input)
            if result is not None:
                self.logger.info(f"Plugin handled input: {result[:50]}")
                return result
        except Exception as e:
            self.logger.debug(f"Plugin execution error: {e}")
        return None

    def _execute_plan(self, plan: TaskPlan) -> str:
        """Execute a task plan and return the final response.

        Iterates through subtasks, executing each one. For subtasks
        that require LLM interaction, sends the context to the LLM.

        Args:
            plan: TaskPlan to execute.

        Returns:
            Final response string.
        """
        results: List[str] = []

        while plan.current_subtask is not None:
            subtask = plan.current_subtask
            subtask.status = TaskPlan.__bases__[0].__bases__  # type: ignore
            # Use proper status
            from voicepilot_cli.agent.planner import TaskStatus
            subtask.status = TaskStatus.IN_PROGRESS

            self.logger.debug(f"Executing subtask: {subtask.description}")

            try:
                if subtask.action == "respond":
                    # This is handled by LLM - collect all non-respond subtask results
                    # and send to LLM at the end
                    subtask.status = TaskStatus.SKIPPED
                elif subtask.action == "calculate":
                    result = self._execute_calculate(subtask.parameters)
                    subtask.result = result
                    subtask.status = TaskStatus.COMPLETED
                    results.append(result)
                elif subtask.action == "weather":
                    result = self._execute_weather(subtask.parameters)
                    subtask.result = result
                    subtask.status = TaskStatus.COMPLETED
                    results.append(result)
                elif subtask.action == "timer":
                    result = self._execute_timer(subtask.parameters)
                    subtask.result = result
                    subtask.status = TaskStatus.COMPLETED
                    results.append(result)
                elif subtask.action in ("file_read", "file_write", "file_list"):
                    result = self._execute_file_op(subtask.action, subtask.parameters)
                    subtask.result = result
                    subtask.status = TaskStatus.COMPLETED
                    results.append(result)
                else:
                    subtask.status = TaskStatus.SKIPPED
            except Exception as e:
                subtask.result = f"Error: {e}"
                subtask.status = TaskStatus.FAILED
                self.logger.error(f"Subtask failed: {e}")

            plan.advance()

        # If we have tool results, send them to the LLM for a natural response
        if results:
            return self._generate_response_with_context(results)
        else:
            # Direct LLM response
            return self._generate_response()

    def _generate_response(self) -> str:
        """Generate a response from the LLM using conversation context.

        Returns:
            LLM response string.
        """
        context = self.memory.get_context()
        try:
            return self.llm.generate(context)
        except Exception as e:
            self.logger.error(f"LLM generation error: {e}")
            return f"Sorry, I encountered an error generating a response: {e}"

    def _generate_response_with_context(self, tool_results: List[str]) -> str:
        """Generate a response incorporating tool/plugin results.

        Args:
            tool_results: List of results from tool/plugin execution.

        Returns:
            LLM response string incorporating tool results.
        """
        # Add tool results as context
        tool_context = "\n".join(f"[Tool Result]: {r}" for r in tool_results)

        # Temporarily add tool context to conversation
        self.memory.add_tool_message(tool_context)

        try:
            return self._generate_response()
        finally:
            # Remove the temporary tool message from memory
            if self.memory._messages:
                self.memory._messages.pop()

    def _execute_calculate(self, params: Dict[str, Any]) -> str:
        """Execute a calculation using the calculator plugin.

        Args:
            params: Calculation parameters including 'expression'.

        Returns:
            Calculation result string.
        """
        try:
            registry = self.plugin_registry
            plugin = registry.get_plugin("calculator")
            if plugin:
                return plugin.execute(params.get("expression", ""))
        except Exception as e:
            self.logger.error(f"Calculation error: {e}")
        return "Calculator plugin not available."

    def _execute_weather(self, params: Dict[str, Any]) -> str:
        """Execute a weather query using the weather plugin.

        Args:
            params: Weather query parameters including 'location'.

        Returns:
            Weather information string.
        """
        try:
            registry = self.plugin_registry
            plugin = registry.get_plugin("weather")
            if plugin:
                return plugin.execute(params.get("location", "auto"))
        except Exception as e:
            self.logger.error(f"Weather query error: {e}")
        return "Weather plugin not available."

    def _execute_timer(self, params: Dict[str, Any]) -> str:
        """Execute a timer using the timer plugin.

        Args:
            params: Timer parameters including 'duration' and 'unit'.

        Returns:
            Timer confirmation string.
        """
        try:
            registry = self.plugin_registry
            plugin = registry.get_plugin("timer")
            if plugin:
                duration = params.get("duration", 0)
                unit = params.get("unit", "秒")
                return plugin.execute(f"{duration} {unit}")
        except Exception as e:
            self.logger.error(f"Timer error: {e}")
        return "Timer plugin not available."

    def _execute_file_op(self, action: str, params: Dict[str, Any]) -> str:
        """Execute a file operation using the file_ops plugin.

        Args:
            action: File operation type ('file_read', 'file_write', 'file_list').
            params: File operation parameters.

        Returns:
            Operation result string.
        """
        try:
            registry = self.plugin_registry
            plugin = registry.get_plugin("file_ops")
            if plugin:
                return plugin.execute(f"{action}:{params}")
        except Exception as e:
            self.logger.error(f"File operation error: {e}")
        return "File operations plugin not available."

    def run_text_mode(self, use_tui: bool = True) -> int:
        """Run the agent in text-only interactive mode.

        Args:
            use_tui: Whether to use the TUI dashboard (if available).

        Returns:
            Exit code.
        """
        self.logger.info("Starting text mode")

        # Check if TUI is available and requested
        if use_tui and self._check_rich_available():
            return self._run_tui_mode()

        # Plain text mode
        return self._run_plain_text_mode()

    def run_voice_mode(self) -> int:
        """Run the agent in voice interactive mode.

        Combines STT for input and TTS for output with the
        standard conversation loop.

        Returns:
            Exit code.
        """
        self.logger.info("Starting voice mode")

        # Check voice backend availability
        if not self.stt:
            print("Warning: No STT backend available. Falling back to text input.")
        if not self.tts:
            print("Warning: No TTS backend available. Responses will be text only.")

        print("\n" + "=" * 50)
        print("  VoicePilot Voice Mode")
        print("  Commands: /quit, /clear, /help")
        print("=" * 50 + "\n")

        try:
            while True:
                # Get input (voice or text fallback)
                if self.stt:
                    print("\nListening... (speak now, or type to use text)")
                    user_input = self._get_voice_or_text_input()
                else:
                    user_input = input("You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    if self._handle_command(user_input):
                        break
                    continue

                # Process input
                response = self.process_input(user_input)
                print(f"\nAssistant: {response}")

                # Speak response if TTS available
                if self.tts:
                    self.tts.speak(response)

        except KeyboardInterrupt:
            print("\nGoodbye!")
        except Exception as e:
            self.logger.error(f"Voice mode error: {e}")
            print(f"\nError: {e}")
            return 1

        return 0

    def _get_voice_or_text_input(self) -> str:
        """Get input from voice or fall back to text.

        Attempts to record audio and transcribe it. If recording
        fails or times out, falls back to text input.

        Returns:
            Transcribed text or manually typed text.
        """
        try:
            from voicepilot_cli.voice.audio import AudioRecorder
            recorder = AudioRecorder(config=self.config)

            print("(Recording... press Enter to stop)", end="", flush=True)
            audio_data = recorder.record_until_silence()

            if audio_data:
                print("\rTranscribing...          ")
                text = self.stt.transcribe(audio_data)
                if text.strip():
                    print(f"You (voice): {text}")
                    return text

            print("\rNo speech detected. Type instead: ", end="")
            return input().strip()

        except Exception as e:
            self.logger.debug(f"Voice input failed: {e}")
            print(f"\rVoice input failed: {e}. Type instead: ", end="")
            return input().strip()

    def _run_plain_text_mode(self) -> int:
        """Run the agent in plain text mode (no TUI).

        Returns:
            Exit code.
        """
        print("\n" + "=" * 50)
        print("  VoicePilot Text Mode")
        print("  Commands: /quit, /clear, /help, /history")
        print("=" * 50 + "\n")

        try:
            while True:
                try:
                    user_input = input("You: ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    if self._handle_command(user_input):
                        break
                    continue

                # Process and display response
                if self.config.stream_enabled:
                    print("Assistant: ", end="", flush=True)
                    for chunk in self.process_input_stream(user_input):
                        print(chunk, end="", flush=True)
                    print()
                else:
                    response = self.process_input(user_input)
                    print(f"Assistant: {response}")

        except KeyboardInterrupt:
            print("\nGoodbye!")

        return 0

    def _run_tui_mode(self) -> int:
        """Run the agent with TUI dashboard.

        Returns:
            Exit code.
        """
        try:
            from voicepilot_cli.tui.dashboard import TUIDashboard
            dashboard = TUIDashboard(agent=self, config=self.config)
            return dashboard.run()
        except ImportError:
            self.logger.warning("Rich library not available, falling back to plain text")
            return self._run_plain_text_mode()
        except Exception as e:
            self.logger.error(f"TUI error: {e}")
            print(f"TUI error: {e}")
            return self._run_plain_text_mode()

    def _handle_command(self, command: str) -> bool:
        """Handle slash commands.

        Args:
            command: Command string (e.g., '/quit', '/clear').

        Returns:
            True if the session should end, False otherwise.
        """
        cmd = command.lower().strip()

        if cmd in ("/quit", "/exit", "/q"):
            return True
        elif cmd == "/clear":
            self.memory.clear()
            print("Conversation history cleared.")
        elif cmd == "/help":
            self._print_help()
        elif cmd == "/history":
            self._print_history()
        elif cmd == "/config":
            config_data = self.config.to_dict()
            import json
            print(json.dumps(config_data, indent=2, ensure_ascii=False))
        elif cmd == "/save":
            self.memory._save()
            print("Conversation saved.")
        elif cmd.startswith("/model "):
            model_name = command.strip().split(" ", 1)[1]
            self.config.set("llm.model", model_name)
            print(f"Model changed to: {model_name}")
        elif cmd.startswith("/backend "):
            backend_name = command.strip().split(" ", 1)[1]
            self.config.set("llm.backend", backend_name)
            self._llm = None  # Force re-initialization
            print(f"Backend changed to: {backend_name}")
        else:
            print(f"Unknown command: {command}. Type /help for available commands.")

        return False

    def _print_help(self) -> None:
        """Print available commands."""
        help_text = """
Available Commands:
  /quit, /exit, /q    - Exit VoicePilot
  /clear              - Clear conversation history
  /help               - Show this help message
  /history            - Show conversation history
  /config             - Show current configuration
  /save               - Save conversation history
  /model <name>       - Switch LLM model
  /backend <name>     - Switch LLM backend (openai/ollama/glm)
"""
        print(help_text)

    def _print_history(self) -> None:
        """Print conversation history."""
        messages = self.memory.messages
        if not messages:
            print("No conversation history.")
            return

        print(f"\nConversation History ({len(messages)} messages):")
        print("-" * 40)
        for msg in messages:
            role_display = msg.role.upper()
            content_preview = msg.content[:200] + ("..." if len(msg.content) > 200 else "")
            print(f"[{msg.timestamp[:19]}] {role_display}: {content_preview}")
        print("-" * 40)

    def _check_rich_available(self) -> bool:
        """Check if the Rich library is available for TUI.

        Returns:
            True if Rich is installed and TUI is enabled in config.
        """
        if not self.config.get("tui.enabled", True):
            return False
        try:
            import rich  # noqa: F401
            return True
        except ImportError:
            return False
