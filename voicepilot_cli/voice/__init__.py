"""Voice module for VoicePilot-CLI.

Provides speech-to-text (STT), text-to-speech (TTS),
and audio recording/playback utilities.
"""

from voicepilot_cli.voice.stt import STTEngine
from voicepilot_cli.voice.tts import TTSEngine
from voicepilot_cli.voice.audio import AudioRecorder, AudioPlayer

__all__ = ["STTEngine", "TTSEngine", "AudioRecorder", "AudioPlayer"]
