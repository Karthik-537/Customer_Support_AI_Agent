"""Gemini speech-to-text and text-to-speech helpers for the Streamlit UI.

Voice input and spoken replies stay in the frontend so transcribed text can
be sent through the existing `/api/chat` agent entry point.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import re
import wave

from dotenv import load_dotenv
from google.genai import types

from app.agent.llm import get_gemini_client

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_TRANSCRIBE_MODEL = "gemini-3.5-transcribe"
DEFAULT_TTS_MODEL = "gemini-3.8-flash-lite-tts"
DEFAULT_TTS_VOICE = "Kore"
TTS_STYLE = "warm, clear, and helpful customer-service tone"
_EMPTY_TRANSCRIPT_MARKERS = {"", ".", "..", "...", "[silence]", "(silence)"}


def _detect_audio_mime_type(audio_bytes: bytes) -> str:
    """Infer a MIME type from container magic bytes.

    Streamlit microphone recordings are typically WAV, but uploads and
    browsers can produce other formats. Do not assume WAV.
    """
    if len(audio_bytes) >= 12 and audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
        return "audio/wav"
    if audio_bytes.startswith(b"ID3") or audio_bytes[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
        return "audio/mpeg"
    if audio_bytes.startswith(b"OggS"):
        return "audio/ogg"
    if audio_bytes.startswith(b"fLaC"):
        return "audio/flac"
    if len(audio_bytes) >= 8 and audio_bytes[4:8] == b"ftyp":
        return "audio/mp4"
    if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    return "application/octet-stream"


def _speech_text(text: str) -> str:
    """Lightly strip markdown so spoken replies stay natural."""
    cleaned = re.sub(r"[*_`#]+", "", text)
    cleaned = re.sub(r"^\s*[-•]\s+", "", cleaned, flags=re.MULTILINE)
    return " ".join(cleaned.split())


def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe recorded customer audio to text using Gemini.

    Args:
        audio_bytes: Recorded or uploaded audio in its original container.

    Returns:
        Recognized text, or an empty string when speech cannot be recovered.
    """
    if not audio_bytes:
        logger.warning("Transcription skipped: empty audio payload")
        return ""

    mime_type = _detect_audio_mime_type(audio_bytes)
    if mime_type == "application/octet-stream":
        logger.warning("Transcription skipped: unrecognized audio format")
        return ""

    model = os.getenv("GEMINI_TRANSCRIBE_MODEL", DEFAULT_TRANSCRIBE_MODEL)

    try:
        client = get_gemini_client().client
        response = client.models.generate_content(
            model=model,
            contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)],
            config=types.GenerateContentConfig(
                audio_transcription_config=types.AudioTranscriptionConfig(
                    mode=types.AudioTranscriptionConfigMode.SMART,
                ),
            ),
        )
    except ValueError as exc:
        logger.error("Transcription is unavailable: %s", exc)
        return ""
    except Exception as exc:
        logger.error("Gemini transcription failed: %s", exc)
        return ""

    transcript = (getattr(response, "text", None) or "").strip()
    if transcript.lower() in _EMPTY_TRANSCRIPT_MARKERS:
        logger.info("Transcription returned no usable speech")
        return ""
    return transcript


def generate_voice_reply(text: str) -> bytes:
    """Synthesize a spoken customer-service reply from agent text.

    Args:
        text: Final CSA agent response. Intermediate tool output must not
            be passed here.

    Returns:
        WAV audio bytes suitable for Streamlit playback, or empty bytes
        when synthesis fails.
    """
    spoken = _speech_text(text or "")
    if not spoken:
        logger.warning("Voice reply skipped: empty text")
        return b""

    model = os.getenv("GEMINI_TTS_MODEL", DEFAULT_TTS_MODEL)
    voice_name = os.getenv("GEMINI_TTS_VOICE", DEFAULT_TTS_VOICE)

    try:
        client = get_gemini_client().client
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            text=spoken,
                            speech_metadata=types.SpeechMetadata(style=TTS_STYLE),
                        )
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(voice=voice_name),
                ),
            ),
        )
    except ValueError as exc:
        logger.error("Voice reply is unavailable: %s", exc)
        return b""
    except Exception as exc:
        logger.error("Gemini speech generation failed: %s", exc)
        return b""

    audio_bytes = _extract_audio_bytes(response)
    if not audio_bytes:
        logger.error("Gemini TTS returned no audio output")
        return b""
    return audio_bytes


def _extract_audio_bytes(response: object) -> bytes:
    """Return WAV bytes from a Gemini TTS generate_content response."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return b""

    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []
    for part in parts:
        inline_data = getattr(part, "inline_data", None)
        if inline_data is None:
            continue
        data = getattr(inline_data, "data", None)
        if not data:
            continue
        if isinstance(data, str):
            try:
                data = base64.b64decode(data)
            except Exception:
                logger.error("Could not decode TTS audio payload")
                return b""
        if not isinstance(data, (bytes, bytearray)):
            return b""
        audio_bytes = bytes(data)
        mime_type = (getattr(inline_data, "mime_type", None) or "").lower()
        if audio_bytes.startswith(b"RIFF") or "wav" in mime_type:
            return audio_bytes
        return _pcm_to_wav(audio_bytes)
    return b""


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Wrap headerless 16-bit PCM in a WAV container for Streamlit playback."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def spoken_replies_enabled() -> bool:
    """Return whether spoken replies should be generated."""
    return os.getenv("VOICE_REPLIES_DEFAULT", "true").strip().lower() in {"1", "true", "yes", "on"}
