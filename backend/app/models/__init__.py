"""Domain models and enumerations for FlashiFi.

All public enumerations and helper utilities are re-exported from this
package for convenient access::

    from app.models import InputType, AudioFormat, AudioQuality
"""

from app.models.enums import (
    AudioFormat,
    AudioQuality,
    DownloadStage,
    FORMAT_EXTENSIONS,
    InputType,
    SourcePlatform,
    VALID_QUALITY_FOR_FORMAT,
    get_default_quality,
)

__all__ = [
    "AudioFormat",
    "AudioQuality",
    "DownloadStage",
    "FORMAT_EXTENSIONS",
    "InputType",
    "SourcePlatform",
    "VALID_QUALITY_FOR_FORMAT",
    "get_default_quality",
]
