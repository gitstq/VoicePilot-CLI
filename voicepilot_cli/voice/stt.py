"""
Speech-to-text engine for VoicePilot-CLI.

Supports multiple backends with graceful degradation:
- whisper: OpenAI Whisper (requires openai-whisper)
- pocketsphinx: CMU PocketSphinx (requires pocketsphinx)
- system: Falls back to text input (always available)
"""

from typing import Any, Dict, Optional

from voicepilot_cli.utils.logger import get_logger


class STTEngine:
    """Speech-to-text engine with multi-backend support.

    Automatically selects the best available backend and falls
    back gracefully when dependencies are missing.

    Attributes:
        backend: Name of the active backend.
        available: Whether any STT backend is available.
    """

    def __init__(self, backend: str = "system", config: Optional[Any] = None) -> None:
        """Initialize the STT engine.

        Args:
            backend: Preferred backend name ('whisper', 'pocketsphinx', 'system').
            config: Optional VoicePilotConfig instance.
        """
        self.logger = get_logger("stt")
        self._config = config
        self._backend_instance = None
        self.backend = "system"
        self.available = False

        # Try to initialize the requested backend
        backends_to_try = [backend, "whisper", "pocketsphinx", "system"]
        for name in backends_to_try:
            if name == "system":
                self.backend = "system"
                self.available = True
                self.logger.info("Using system (text input) STT backend")
                break

            instance = self._try_init_backend(name)
            if instance is not None:
                self._backend_instance = instance
                self.backend = name
                self.available = True
                self.logger.info(f"Using STT backend: {name}")
                break

    def _try_init_backend(self, name: str):
        """Try to initialize a specific STT backend.

        Args:
            name: Backend name to try.

        Returns:
            Backend instance or None if not available.
        """
        if name == "whisper":
            return self._try_init_whisper()
        elif name == "pocketsphinx":
            return self._try_init_pocketsphinx()
        return None

    def _try_init_whisper(self):
        """Try to initialize the Whisper STT backend.

        Returns:
            Whisper model instance or None.
        """
        try:
            import whisper
            model_name = "base"  # Use base model for balance of speed/accuracy
            self.logger.info(f"Loading Whisper model: {model_name}")
            model = whisper.load_model(model_name)
            return model
        except ImportError:
            self.logger.debug("Whisper not installed. Install with: pip install openai-whisper")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Whisper: {e}")
        return None

    def _try_init_pocketsphinx(self):
        """Try to initialize the PocketSphinx STT backend.

        Returns:
            PocketSphinx decoder instance or None.
        """
        try:
            import sphinxbase
            import pocketsphinx
            self.logger.info("Initializing PocketSphinx")
            # PocketSphinx requires acoustic model, dictionary, and language model
            # For now, return a simple wrapper
            return {"backend": "pocketsphinx"}
        except ImportError:
            self.logger.debug("PocketSphinx not installed. Install with: pip install pocketsphinx")
        except Exception as e:
            self.logger.warning(f"Failed to initialize PocketSphinx: {e}")
        return None

    def transcribe(self, audio_data: bytes, language: Optional[str] = None) -> str:
        """Transcribe audio data to text.

        Args:
            audio_data: Raw audio data (WAV format bytes).
            language: Language code (e.g., 'zh-CN', 'en-US').
                     If None, uses config or auto-detects.

        Returns:
            Transcribed text string.
        """
        if self.backend == "system":
            return ""

        lang = language
        if lang is None and self._config:
            lang = self._config.get("voice.language", "zh-CN")

        if self.backend == "whisper" and self._backend_instance is not None:
            return self._transcribe_whisper(audio_data, lang)
        elif self.backend == "pocketsphinx" and self._backend_instance is not None:
            return self._transcribe_pocketsphinx(audio_data, lang)

        return ""

    def _transcribe_whisper(self, audio_data: bytes, language: Optional[str] = None) -> str:
        """Transcribe using Whisper backend.

        Args:
            audio_data: WAV audio bytes.
            language: Language hint.

        Returns:
            Transcribed text.
        """
        try:
            import numpy as np
            import io

            # Whisper expects a numpy array or file path
            # Convert WAV bytes to numpy array
            audio_file = io.BytesIO(audio_data)
            result = self._backend_instance.transcribe(
                audio_file,
                language=language,
                fp16=False,
            )
            return result.get("text", "").strip()
        except Exception as e:
            self.logger.error(f"Whisper transcription error: {e}")
            return ""

    def _transcribe_pocketsphinx(self, audio_data: bytes, language: Optional[str] = None) -> str:
        """Transcribe using PocketSphinx backend.

        Args:
            audio_data: WAV audio bytes.
            language: Language hint.

        Returns:
            Transcribed text.
        """
        try:
            # PocketSphinx integration would go here
            # This requires acoustic models to be installed
            self.logger.warning("PocketSphinx transcription not fully implemented")
            return ""
        except Exception as e:
            self.logger.error(f"PocketSphinx transcription error: {e}")
            return ""

    def transcribe_file(self, filepath: str, language: Optional[str] = None) -> str:
        """Transcribe an audio file to text.

        Args:
            filepath: Path to audio file (WAV, MP3, etc.).
            language: Language code.

        Returns:
            Transcribed text string.
        """
        if self.backend == "whisper" and self._backend_instance is not None:
            try:
                lang = language or (self._config.get("voice.language", "zh-CN") if self._config else None)
                result = self._backend_instance.transcribe(
                    filepath,
                    language=lang,
                    fp16=False,
                )
                return result.get("text", "").strip()
            except Exception as e:
                self.logger.error(f"File transcription error: {e}")
                return ""

        return ""

    @property
    def supported_languages(self) -> list:
        """Get list of supported languages.

        Returns:
            List of supported language codes.
        """
        if self.backend == "whisper":
            return ["zh", "en", "ja", "ko", "fr", "de", "es", "pt", "ru", "ar"]
        return []
