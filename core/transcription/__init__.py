"""Optional local speech-to-text services."""

from core.transcription.models import (
    TranscriptionCapabilities,
    TranscriptionPlan,
    TranscriptionRequest,
    TranscriptionState,
    TranscriptionTask,
)
from core.transcription.service import SpeechModel, SpeechModelManager, TranscriptionService

__all__ = [
    "SpeechModel",
    "SpeechModelManager",
    "TranscriptionCapabilities",
    "TranscriptionPlan",
    "TranscriptionRequest",
    "TranscriptionService",
    "TranscriptionState",
    "TranscriptionTask",
]
