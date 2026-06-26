"""
Tests for app.services.ranking.RankingService.
Validates that the ranking algorithm correctly prioritises official channels,
title similarity, duration proximity, and topic channels.
"""
from app.services.ranking import RankingService
from app.services.youtube import SearchResult


def _make_result(**kwargs) -> SearchResult:
    """Factory helper that fills in sensible defaults for SearchResult fields."""
    defaults = {
        "video_id": "test123",
        "title": "Test Song",
        "uploader": "Test Channel",
        "channel_id": "UC123",
        "duration": 200,
        "view_count": 1_000_000,
        "url": "https://youtube.com/watch?v=test123",
        "is_official": False,
    }
    defaults.update(kwargs)
    return SearchResult(**defaults)


class TestRankingService:
    """Ranking-service behaviour."""

    def test_official_channel_ranked_higher(self):
        """VEVO / official-flag videos should outrank generic uploads."""
        service = RankingService()
        results = [
            _make_result(
                title="Song Name",
                uploader="Random Channel",
                is_official=False,
            ),
            _make_result(
                title="Song Name",
                uploader="Artist VEVO",
                is_official=True,
                video_id="official",
            ),
        ]
        best = service.rank_results(results, "Song Name", "Artist")
        assert best is not None
        assert best.video_id == "official"

    def test_title_similarity(self):
        """The result whose title best matches the query should rank first."""
        service = RankingService()
        results = [
            _make_result(title="Completely Different Title", video_id="wrong"),
            _make_result(title="Believer", video_id="correct"),
        ]
        best = service.rank_results(results, "Believer")
        assert best is not None
        assert best.video_id == "correct"

    def test_duration_similarity(self):
        """When titles are equal, the result closer in duration should win."""
        service = RankingService()
        results = [
            _make_result(title="Song", duration=600, video_id="long"),  # 10 min
            _make_result(title="Song", duration=205, video_id="close"),  # ~3:25
        ]
        best = service.rank_results(results, "Song", target_duration=200)
        assert best is not None
        assert best.video_id == "close"

    def test_topic_channel_ranked_higher(self):
        """YouTube Auto-generated 'Topic' channels should be preferred."""
        service = RankingService()
        results = [
            _make_result(title="Song", uploader="Random", video_id="random"),
            _make_result(
                title="Song", uploader="Artist - Topic", video_id="topic"
            ),
        ]
        best = service.rank_results(results, "Song", "Artist")
        assert best is not None
        assert best.video_id == "topic"

    def test_empty_results_returns_none(self):
        """An empty result list should yield None, not crash."""
        service = RankingService()
        result = service.rank_results([], "Song")
        assert result is None
