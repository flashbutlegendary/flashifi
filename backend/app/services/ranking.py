"""
Search result ranking service.

Uses a multi-signal scoring algorithm to rank YouTube search results against a
target track (title, artist, duration) to find the best matching video.
"""

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from app.services.youtube import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class ScoredResult:
    """Represents a search result and its computed similarity score."""

    result: SearchResult
    score: float
    breakdown: dict[str, float]


class RankingService:
    """Calculates compatibility scores for search results to identify matches."""

    # Weights for scoring (must sum to 1.0)
    TITLE_WEIGHT = 0.25
    ARTIST_WEIGHT = 0.15
    OFFICIAL_CHANNEL_WEIGHT = 0.20
    DURATION_WEIGHT = 0.10
    OFFICIAL_KEYWORDS_WEIGHT = 0.10
    VIEW_COUNT_WEIGHT = 0.10
    UPLOADER_REPUTATION_WEIGHT = 0.05
    ARTIST_TOPIC_WEIGHT = 0.05

    OFFICIAL_KEYWORDS = {
        "official audio",
        "official music video",
        "official video",
        "official lyric video",
        "lyric video",
        "lyrics",
    }
    TOPIC_SUFFIX = " - Topic"
    VEVO_SUFFIX = "VEVO"

    def rank_results(
        self,
        results: list[SearchResult],
        target_title: str,
        target_artist: str | None = None,
        target_duration: int | None = None,
    ) -> SearchResult | None:
        """Rank search results and return the highest-scoring result.

        Evaluates title, artist name, video duration, and publisher reputation
        signals to compute a score between 0.0 and 1.0 for each result.

        Args:
            results: The search results to rank.
            target_title: The expected track title.
            target_artist: The expected artist name.
            target_duration: The expected track duration in seconds.

        Returns:
            The best matching ``SearchResult`` or ``None`` if list is empty.
        """
        if not results:
            return None

        scored_results: list[ScoredResult] = []
        for res in results:
            scored = self._score_result(res, target_title, target_artist, target_duration)
            scored_results.append(scored)

        # Sort by score descending
        scored_results.sort(key=lambda x: x.score, reverse=True)

        best = scored_results[0]
        logger.info(
            "Ranking complete",
            extra={
                "best_id": best.result.video_id,
                "best_title": best.result.title,
                "best_score": round(best.score, 3),
                "breakdown": {k: round(v, 3) for k, v in best.breakdown.items()},
            },
        )
        return best.result

    def _score_result(
        self,
        result: SearchResult,
        target_title: str,
        target_artist: str | None,
        target_duration: int | None,
    ) -> ScoredResult:
        """Compute the weighted score for a single search result."""
        # 1. Title similarity
        title_score = self._title_similarity(result.title, target_title)

        # 2. Artist similarity
        artist_score = 0.0
        if target_artist:
            artist_score = self._title_similarity(result.uploader, target_artist)
            # If the uploader is a topic channel, strip " - Topic" and check similarity again
            if result.uploader.endswith(self.TOPIC_SUFFIX):
                stripped_uploader = result.uploader[: -len(self.TOPIC_SUFFIX)]
                topic_artist_score = self._title_similarity(stripped_uploader, target_artist)
                artist_score = max(artist_score, topic_artist_score)

        # 3. Official channel verification
        official_channel_score = 1.0 if result.is_official else 0.0
        if self.VEVO_SUFFIX.lower() in result.uploader.lower():
            official_channel_score = 1.0

        # 4. Duration proximity
        duration_score = 1.0
        if target_duration is not None and target_duration > 0:
            duration_score = self._duration_similarity(result.duration, target_duration)

        # 5. Official keywords in title
        official_keywords_score = 0.0
        result_title_lower = result.title.lower()
        if any(kw in result_title_lower for kw in self.OFFICIAL_KEYWORDS):
            official_keywords_score = 1.0

        # 6. View count score (logarithmic mapping up to 10M views)
        view_count_score = 0.0
        if result.view_count > 0:
            # log10(10,000,000) = 7. Capped at 1.0
            import math
            view_count_score = min(1.0, math.log10(result.view_count) / 7.0)

        # 7. Uploader reputation
        uploader_reputation_score = 0.0
        if self.VEVO_SUFFIX.lower() in result.uploader.lower() or result.is_official:
            uploader_reputation_score = 1.0
        elif "music" in result.uploader.lower() or "records" in result.uploader.lower():
            uploader_reputation_score = 0.5

        # 8. Topic channel match
        topic_score = 1.0 if result.uploader.endswith(self.TOPIC_SUFFIX) else 0.0

        # Weighted calculation
        breakdown = {
            "title": title_score * self.TITLE_WEIGHT,
            "artist": artist_score * self.ARTIST_WEIGHT if target_artist else 0.0,
            "official_channel": official_channel_score * self.OFFICIAL_CHANNEL_WEIGHT,
            "duration": duration_score * self.DURATION_WEIGHT if target_duration else 0.0,
            "official_keywords": official_keywords_score * self.OFFICIAL_KEYWORDS_WEIGHT,
            "view_count": view_count_score * self.VIEW_COUNT_WEIGHT,
            "uploader_reputation": uploader_reputation_score * self.UPLOADER_REPUTATION_WEIGHT,
            "topic": topic_score * self.ARTIST_TOPIC_WEIGHT,
        }

        # Normalize weights if target fields are missing
        total_weight = (
            self.TITLE_WEIGHT
            + (self.ARTIST_WEIGHT if target_artist else 0.0)
            + self.OFFICIAL_CHANNEL_WEIGHT
            + (self.DURATION_WEIGHT if target_duration else 0.0)
            + self.OFFICIAL_KEYWORDS_WEIGHT
            + self.VIEW_COUNT_WEIGHT
            + self.UPLOADER_REPUTATION_WEIGHT
            + self.ARTIST_TOPIC_WEIGHT
        )

        final_score = sum(breakdown.values()) / total_weight

        return ScoredResult(result=result, score=final_score, breakdown=breakdown)

    def _title_similarity(self, a: str, b: str) -> float:
        """Calculate similarity ratio between two strings.

        Converts strings to lowercase, removes punctuation/special characters,
        strips extra whitespace, and computes a SequenceMatcher ratio.
        """
        def clean_string(s: str) -> str:
            s_clean = s.lower()
            # Remove official keywords to avoid penalizing matches
            for kw in self.OFFICIAL_KEYWORDS:
                s_clean = s_clean.replace(kw, "")
            # Remove non-alphanumeric chars (keep spaces)
            s_clean = re.sub(r"[^\w\s]", "", s_clean)
            # Remove extra spaces
            return " ".join(s_clean.split())

        clean_a = clean_string(a)
        clean_b = clean_string(b)

        if not clean_a or not clean_b:
            return 0.0

        return SequenceMatcher(None, clean_a, clean_b).ratio()

    def _duration_similarity(self, actual: int, target: int) -> float:
        """Compute duration similarity score.

        Returns 1.0 for a perfect match, scaling down linearly to 0.0 as the
        difference in duration approaches the target duration itself (or 30s
        for short tracks).
        """
        diff = abs(actual - target)
        if diff == 0:
            return 1.0

        # Scale based on target size, minimum threshold of 30 seconds
        tolerance = max(30.0, float(target))
        return max(0.0, 1.0 - (diff / tolerance))
