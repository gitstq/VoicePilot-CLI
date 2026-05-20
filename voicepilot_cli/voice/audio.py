"""
Audio recording and playback utilities for VoicePilot-CLI.

Provides cross-platform audio recording with VAD (Voice Activity Detection)
and audio playback capabilities. Uses only Python stdlib + optional
sounddevice for recording.
"""

import array
import math
import struct
import sys
import tempfile
import threading
import time
import wave
from typing import Any, BinaryIO, Optional, Tuple

from voicepilot_cli.utils.logger import get_logger


class AudioRecorder:
    """Audio recorder with VAD (Voice Activity Detection).

    Records audio from the microphone with energy-based VAD to
    automatically detect speech segments and silence.

    Attributes:
        sample_rate: Audio sample rate in Hz.
        channels: Number of audio channels.
        sample_width: Bytes per sample.
        vad_enabled: Whether VAD is enabled.
        vad_threshold: Energy threshold for VAD detection.
        silence_duration: Seconds of silence before stopping recording.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        """Initialize the audio recorder.

        Args:
            config: Optional VoicePilotConfig instance for settings.
        """
        self.logger = get_logger("audio")

        # Load configuration
        if config:
            self.sample_rate = config.get("voice.sample_rate", 16000)
            self.channels = config.get("voice.channels", 1)
            self.vad_enabled = config.get("voice.vad_enabled", True)
            self.vad_threshold = config.get("voice.vad_threshold", 500)
            self.silence_duration = config.get("voice.vad_silence_duration", 1.0)
            self.recording_timeout = config.get("voice.recording_timeout", 30)
        else:
            self.sample_rate = 16000
            self.channels = 1
            self.vad_enabled = True
            self.vad_threshold = 500
            self.silence_duration = 1.0
            self.recording_timeout = 30

        self.sample_width = 2  # 16-bit audio
        self._recording = False
        self._audio_data = bytearray()

    def record(self, duration: float) -> bytes:
        """Record audio for a fixed duration.

        Args:
            duration: Recording duration in seconds.

        Returns:
            Recorded audio as WAV bytes.
        """
        self.logger.info(f"Recording for {duration}s")

        try:
            import sounddevice as sd

            frames = int(duration * self.sample_rate)
            recording = sd.rec(
                frames,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
            )
            sd.wait()  # Wait until recording is finished

            # Convert to WAV bytes
            return self._numpy_to_wav(recording)
        except ImportError:
            self.logger.warning(
                "sounddevice not installed. Install with: pip install sounddevice"
            )
            return b""
        except Exception as e:
            self.logger.error(f"Recording error: {e}")
            return b""

    def record_until_silence(self) -> bytes:
        """Record audio until silence is detected (VAD mode).

        Records continuously and stops when the configured
        duration of silence is detected.

        Returns:
            Recorded audio as WAV bytes.
        """
        self.logger.info("Recording until silence (VAD)")

        try:
            import sounddevice as sd
            import numpy as np

            self._recording = True
            self._audio_data = bytearray()
            silence_start: Optional[float] = None
            start_time = time.time()

            def audio_callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
                """Callback for audio stream processing."""
                if not self._recording:
                    raise sd.CallbackStop

                # Check recording timeout
                if time.time() - start_time > self.recording_timeout:
                    self._recording = False
                    raise sd.CallbackStop

                # Calculate audio energy for VAD
                audio_array = indata[:, 0] if self.channels == 1 else indata.mean(axis=1)
                energy = float(np.sqrt(np.mean(audio_array ** 2)))

                # Store audio data
                self._audio_data.extend(indata.tobytes())

                # VAD logic
                if self.vad_enabled:
                    if energy > self.vad_threshold:
                        silence_start = None  # Reset silence timer
                    elif silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start >= self.silence_duration:
                        self._recording = False
                        raise sd.CallbackStop

            # Start recording stream
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=audio_callback,
                blocksize=int(self.sample_rate * 0.1),  # 100ms blocks
            ):
                while self._recording:
                    time.sleep(0.05)

            # Convert raw bytes to WAV
            if self._audio_data:
                return self._raw_to_wav(bytes(self._audio_data))
            return b""

        except ImportError:
            self.logger.warning(
                "sounddevice not installed. Cannot record audio."
            )
            return b""
        except Exception as e:
            self.logger.error(f"VAD recording error: {e}")
            return b""

    def record_manual(self) -> bytes:
        """Record audio with manual start/stop (press Enter to stop).

        Returns:
            Recorded audio as WAV bytes.
        """
        self.logger.info("Recording (press Enter to stop)...")

        try:
            import sounddevice as sd

            self._recording = True
            self._audio_data = bytearray()
            start_time = time.time()

            def audio_callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
                """Callback for audio stream processing."""
                if not self._recording:
                    raise sd.CallbackStop
                if time.time() - start_time > self.recording_timeout:
                    self._recording = False
                    raise sd.CallbackStop
                self._audio_data.extend(indata.tobytes())

            # Start recording in a thread
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=audio_callback,
                blocksize=int(self.sample_rate * 0.1),
            )
            stream.start()

            # Wait for Enter key
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass

            self._recording = False
            stream.stop()
            stream.close()

            if self._audio_data:
                return self._raw_to_wav(bytes(self._audio_data))
            return b""

        except ImportError:
            self.logger.warning(
                "sounddevice not installed. Cannot record audio."
            )
            return b""
        except Exception as e:
            self.logger.error(f"Manual recording error: {e}")
            return b""

    def stop(self) -> None:
        """Stop any ongoing recording."""
        self._recording = False

    def _raw_to_wav(self, raw_data: bytes) -> bytes:
        """Convert raw PCM audio data to WAV format bytes.

        Args:
            raw_data: Raw PCM audio bytes (16-bit signed integers).

        Returns:
            WAV formatted bytes.
        """
        import io

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.sample_width)
            wf.setframerate(self.sample_rate)
            wf.writeframes(raw_data)

        return buffer.getvalue()

    def _numpy_to_wav(self, numpy_array: Any) -> bytes:
        """Convert numpy array to WAV format bytes.

        Args:
            numpy_array: NumPy array of audio samples.

        Returns:
            WAV formatted bytes.
        """
        import io

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.sample_width)
            wf.setframerate(self.sample_rate)
            wf.writeframes(numpy_array.tobytes())

        return buffer.getvalue()

    @staticmethod
    def compute_rms_energy(audio_data: bytes, sample_width: int = 2) -> float:
        """Compute RMS energy of audio data.

        Used for VAD threshold calibration.

        Args:
            audio_data: Raw PCM audio bytes.
            sample_width: Bytes per sample (default 2 for 16-bit).

        Returns:
            RMS energy value.
        """
        if not audio_data:
            return 0.0

        # Convert bytes to samples
        num_samples = len(audio_data) // sample_width
        if num_samples == 0:
            return 0.0

        if sample_width == 2:
            fmt = f"<{num_samples}h"
        elif sample_width == 1:
            fmt = f"<{num_samples}B"
        else:
            return 0.0

        try:
            samples = struct.unpack(fmt, audio_data[:num_samples * sample_width])
        except struct.error:
            return 0.0

        # Compute RMS
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / num_samples)
        return rms


class AudioPlayer:
    """Audio file player with cross-platform support.

    Plays audio files using the system's default audio player
    or optional sounddevice for direct playback.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        """Initialize the audio player.

        Args:
            config: Optional VoicePilotConfig instance.
        """
        self.logger = get_logger("audio_player")

    def play_file(self, filepath: str, blocking: bool = True) -> bool:
        """Play an audio file.

        Args:
            filepath: Path to the audio file.
            blocking: Whether to wait for playback to finish.

        Returns:
            True if playback started successfully.
        """
        import subprocess
        import platform

        if not filepath or not os.path.exists(filepath):
            self.logger.error(f"Audio file not found: {filepath}")
            return False

        system = platform.system()
        cmd = self._get_play_command(filepath, system)

        try:
            if blocking:
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                )
            else:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            return True
        except FileNotFoundError:
            self.logger.warning(f"No audio player found for {system}")
            return False
        except subprocess.TimeoutExpired:
            self.logger.warning("Audio playback timed out")
            return False
        except Exception as e:
            self.logger.error(f"Playback error: {e}")
            return False

    def play_bytes(self, audio_data: bytes, blocking: bool = True) -> bool:
        """Play audio from bytes (WAV format).

        Args:
            audio_data: WAV audio bytes.
            blocking: Whether to wait for playback to finish.

        Returns:
            True if playback started successfully.
        """
        try:
            import sounddevice as sd
            import io
            import wave

            # Parse WAV from bytes
            wf = wave.open(io.BytesIO(audio_data), "rb")
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            frames = wf.readframes(wf.getnframes())
            wf.close()

            import numpy as np
            audio_array = np.frombuffer(frames, dtype=np.int16)

            if blocking:
                sd.play(audio_array, samplerate=sample_rate)
                sd.wait()
            else:
                threading.Thread(
                    target=lambda: (sd.play(audio_array, samplerate=sample_rate), sd.wait()),
                    daemon=True,
                ).start()

            return True
        except ImportError:
            # Fall back to file-based playback
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            try:
                result = self.play_file(temp_path, blocking)
                return result
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
        except Exception as e:
            self.logger.error(f"Byte playback error: {e}")
            return False

    def _get_play_command(self, filepath: str, system: str) -> list:
        """Get the system-appropriate audio playback command.

        Args:
            filepath: Path to audio file.
            system: OS name ('Linux', 'Darwin', 'Windows').

        Returns:
            Command as a list of strings.
        """
        if system == "Linux":
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
        elif system == "Darwin":
            return ["afplay", filepath]
        elif system == "Windows":
            return [
                "powershell", "-c",
                f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"
            ]
        return ["aplay", filepath]


# Need os import at module level
import os
