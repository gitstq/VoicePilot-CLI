"""
Text-to-speech engine for VoicePilot-CLI.

Supports multiple backends with graceful degradation:
- pyttsx3: Offline TTS using system speech engines
- edge-tts: Microsoft Edge TTS (requires internet)
- system: No audio output (text only, always available)
"""

import asyncio
import subprocess
import sys
import tempfile
import os
from typing import Any, Optional

from voicepilot_cli.utils.logger import get_logger


class TTSEngine:
    """Text-to-speech engine with multi-backend support.

    Automatically selects the best available backend and falls
    back gracefully when dependencies are missing.

    Attributes:
        backend: Name of the active backend.
        available: Whether any TTS backend is available (beyond system).
    """

    def __init__(self, backend: str = "system", config: Optional[Any] = None) -> None:
        """Initialize the TTS engine.

        Args:
            backend: Preferred backend name ('pyttsx3', 'edge-tts', 'system').
            config: Optional VoicePilotConfig instance.
        """
        self.logger = get_logger("tts")
        self._config = config
        self._backend_instance = None
        self.backend = "system"
        self.available = False

        # Try to initialize the requested backend
        backends_to_try = [backend, "pyttsx3", "edge-tts", "system"]
        for name in backends_to_try:
            if name == "system":
                self.backend = "system"
                self.available = False
                self.logger.info("Using system (text only) TTS backend")
                break

            if self._try_init_backend(name):
                self.backend = name
                self.available = True
                self.logger.info(f"Using TTS backend: {name}")
                break

    def _try_init_backend(self, name: str) -> bool:
        """Try to initialize a specific TTS backend.

        Args:
            name: Backend name to try.

        Returns:
            True if backend was successfully initialized.
        """
        if name == "pyttsx3":
            return self._try_init_pyttsx3()
        elif name == "edge-tts":
            return self._try_init_edge_tts()
        return False

    def _try_init_pyttsx3(self) -> bool:
        """Try to initialize the pyttsx3 TTS backend.

        Returns:
            True if successful.
        """
        try:
            import pyttsx3
            self._backend_instance = pyttsx3.init()
            # Configure voice properties
            rate = 180  # Speaking rate
            if self._config:
                rate = self._config.get("voice.tts_rate", 180)
            self._backend_instance.setProperty("rate", rate)
            self.logger.info("pyttsx3 TTS initialized")
            return True
        except ImportError:
            self.logger.debug("pyttsx3 not installed. Install with: pip install pyttsx3")
        except Exception as e:
            self.logger.warning(f"Failed to initialize pyttsx3: {e}")
        return False

    def _try_init_edge_tts(self) -> bool:
        """Try to initialize the edge-tts TTS backend.

        Returns:
            True if successful.
        """
        try:
            import edge_tts
            # edge-tts is async, we just verify it's importable
            self._backend_instance = "edge-tts"
            self.logger.info("edge-tts TTS initialized")
            return True
        except ImportError:
            self.logger.debug("edge-tts not installed. Install with: pip install edge-tts")
        except Exception as e:
            self.logger.warning(f"Failed to initialize edge-tts: {e}")
        return False

    def speak(self, text: str, wait: bool = True) -> None:
        """Speak the given text using the active TTS backend.

        Args:
            text: Text to speak.
            wait: Whether to block until speech is complete.
        """
        if not text.strip():
            return

        if self.backend == "system":
            # No audio output in system mode
            return

        if self.backend == "pyttsx3" and self._backend_instance is not None:
            self._speak_pyttsx3(text, wait)
        elif self.backend == "edge-tts":
            self._speak_edge_tts(text, wait)

    def _speak_pyttsx3(self, text: str, wait: bool) -> None:
        """Speak using pyttsx3 backend.

        Args:
            text: Text to speak.
            wait: Whether to wait for completion.
        """
        try:
            engine = self._backend_instance
            engine.say(text)
            if wait:
                engine.runAndWait()
            else:
                # Start in a non-blocking way
                engine.startLoop(useDriverLoop=False)
        except Exception as e:
            self.logger.error(f"pyttsx3 speech error: {e}")

    def _speak_edge_tts(self, text: str, wait: bool) -> None:
        """Speak using edge-tts backend.

        Uses edge-tts CLI to generate audio and plays it with system player.

        Args:
            text: Text to speak.
            wait: Whether to wait for completion.
        """
        try:
            voice = "zh-CN-XiaoxiaoNeural"
            if self._config:
                voice = self._config.get("voice.tts_voice", "zh-CN-XiaoxiaoNeural")

            # Generate audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name

            # Run edge-tts command
            cmd = [
                sys.executable, "-m", "edge_tts",
                "--voice", voice,
                "--text", text,
                "--write-media", temp_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.logger.error(f"edge-tts error: {result.stderr}")
                return

            # Play the generated audio
            if wait:
                self._play_audio_file(temp_path)
            else:
                # Play in background
                subprocess.Popen(
                    self._get_play_command(temp_path),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            # Clean up temp file after a delay
            if wait:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

        except Exception as e:
            self.logger.error(f"edge-tts speech error: {e}")

    def _play_audio_file(self, filepath: str) -> None:
        """Play an audio file using the system's default audio player.

        Args:
            filepath: Path to the audio file.
        """
        cmd = self._get_play_command(filepath)
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        except subprocess.TimeoutExpired:
            self.logger.warning("Audio playback timed out")
        except FileNotFoundError:
            self.logger.warning("No audio player found")

    def _get_play_command(self, filepath: str) -> list:
        """Get the appropriate command to play an audio file.

        Args:
            filepath: Path to audio file.

        Returns:
            Command as a list of strings.
        """
        import platform
        system = platform.system()

        if system == "Linux":
            # Try common Linux audio players
            for player in ["mpv", "aplay", "paplay", "ffplay", "vlc"]:
                try:
                    subprocess.run(
                        [player, "--version"],
                        capture_output=True,
                        timeout=2,
                    )
                    if player in ("mpv", "ffplay"):
                        return [player, "--really-quiet", filepath]
                    return [player, filepath]
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            return ["aplay", filepath]
        elif system == "Darwin":  # macOS
            return ["afplay", filepath]
        elif system == "Windows":
            # Use PowerShell to play audio
            return [
                "powershell", "-c",
                f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"
            ]
        return ["aplay", filepath]

    def synthesize_to_file(self, text: str, output_path: str) -> bool:
        """Synthesize speech and save to an audio file.

        Args:
            text: Text to synthesize.
            output_path: Path to save the audio file.

        Returns:
            True if successful.
        """
        if self.backend == "edge-tts":
            return self._synthesize_edge_tts_to_file(text, output_path)
        elif self.backend == "pyttsx3" and self._backend_instance is not None:
            return self._synthesize_pyttsx3_to_file(text, output_path)
        return False

    def _synthesize_edge_tts_to_file(self, text: str, output_path: str) -> bool:
        """Synthesize using edge-tts and save to file.

        Args:
            text: Text to synthesize.
            output_path: Output file path.

        Returns:
            True if successful.
        """
        try:
            voice = "zh-CN-XiaoxiaoNeural"
            if self._config:
                voice = self._config.get("voice.tts_voice", "zh-CN-XiaoxiaoNeural")

            cmd = [
                sys.executable, "-m", "edge_tts",
                "--voice", voice,
                "--text", text,
                "--write-media", output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"edge-tts synthesis error: {e}")
            return False

    def _synthesize_pyttsx3_to_file(self, text: str, output_path: str) -> bool:
        """Synthesize using pyttsx3 and save to file.

        Args:
            text: Text to synthesize.
            output_path: Output file path.

        Returns:
            True if successful.
        """
        try:
            engine = self._backend_instance
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            return os.path.exists(output_path)
        except Exception as e:
            self.logger.error(f"pyttsx3 synthesis error: {e}")
            return False

    def list_voices(self) -> list:
        """List available voices for the current backend.

        Returns:
            List of voice information dictionaries.
        """
        if self.backend == "edge-tts":
            return self._list_edge_tts_voices()
        elif self.backend == "pyttsx3" and self._backend_instance is not None:
            return self._list_pyttsx3_voices()
        return []

    def _list_edge_tts_voices(self) -> list:
        """List available edge-tts voices.

        Returns:
            List of voice dicts with 'name', 'language', 'gender' keys.
        """
        try:
            import edge_tts
            voices = asyncio.run(edge_tts.list_voices())
            return [
                {
                    "name": v.get("ShortName", ""),
                    "language": v.get("Locale", ""),
                    "gender": v.get("Gender", ""),
                }
                for v in voices
            ]
        except Exception as e:
            self.logger.error(f"Failed to list edge-tts voices: {e}")
            return []

    def _list_pyttsx3_voices(self) -> list:
        """List available pyttsx3 voices.

        Returns:
            List of voice dicts with 'name', 'id' keys.
        """
        try:
            engine = self._backend_instance
            voices = engine.getProperty("voices")
            return [
                {
                    "name": v.name,
                    "id": v.id,
                }
                for v in voices
            ]
        except Exception as e:
            self.logger.error(f"Failed to list pyttsx3 voices: {e}")
            return []

    def stop(self) -> None:
        """Stop any ongoing speech."""
        if self.backend == "pyttsx3" and self._backend_instance is not None:
            try:
                # Kill any running pyttsx3 loop
                import pyttsx3
                self._backend_instance.stop()
            except Exception:
                pass
