"""Voice message processor."""

import logging
import tempfile
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

from bot.config import config

logger = logging.getLogger(__name__)


class VoiceProcessor:
    """Processes voice messages using OpenAI Whisper and TTS."""

    def __init__(self):
        """Initializes voice processor with config settings."""
        self.model = config.voice.model
        self.language = (
            config.voice.language if config.voice.language != "auto" else None
        )
        self.max_file_size = (
            config.voice.max_file_size * 1024 * 1024
        )  # Convert MB to bytes
        self.client = AsyncOpenAI(api_key=config.openai.api_key)

    async def transcribe(self, voice_file: Path) -> Optional[str]:
        """Transcribes voice message to text using Whisper API."""
        try:
            file_size = voice_file.stat().st_size
            if file_size > self.max_file_size:
                raise ValueError(
                    f"Voice message is too large ({file_size/1024/1024:.1f}MB). "
                    f"Maximum size is {self.max_file_size/1024/1024:.1f}MB. "
                    "Please send a shorter message or compress it externally."
                )

            with open(voice_file, "rb") as audio:
                response = await self.client.audio.transcriptions.create(
                    model=self.model, file=audio, language=self.language
                )
            return response.text

        except Exception as e:
            logger.error(f"Failed to transcribe voice message: {e}")
            return None

    async def text_to_speech(self, text: str) -> Optional[Path]:
        """Converts text to speech using OpenAI TTS API."""
        try:
            # Create temporary file for speech
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                speech_file = Path(tmp_file.name)

            response = await self.client.audio.speech.create(
                model=config.voice.tts["model"],
                voice=config.voice.tts["voice"],
                input=text,
            )

            await response.astream_to_file(speech_file)
            return speech_file

        except Exception as e:
            logger.error(f"Failed to convert text to speech: {e}")
            return None
