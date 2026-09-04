"""
Tests for quality_scorer.

Four defects are pinned here.

1. An unmeasured dimension was still weighted. With no keyword, ``seo`` scored
   0 and its 0.15 weight was applied anyway, so identical content lost 7.5
   points purely for not being handed a keyword.
2. ``content.count("# ")`` also matches inside ``"## "`` and ``"### "``, so H1s
   were over-counted by every subheading present. The "exactly one H1" bonus
   was therefore unreachable for any document with sections.
3. The structure components summed to 85 while the function ended in
   ``min(score, 100)``, implying a maximum that could not be reached.
4. Recommendations were only ever produced for readability and structure, so
   content scoring zero on engagement could be told "Content looks great!".
"""

from __future__ import annotations

import pytest

from quality_scorer import WEIGHTS, ContentQualityScorer

WELL_FORMED = (
    "# Guide to Widgets\n\n"
    "Widgets are useful? Yes. For example, they solve 3 problems.\n\n"
    "## Why widgets\n\nThey work well.\n\n"
    "## How to choose\n\n- size\n- cost\n\n"
    "## Where to buy\n\nGet started today.\n\n"
    "### Online\n\nShops.\n\n"
    "### In person\n\nStores.\n"
)


@pytest.fixture
def scorer():
    return ContentQualityScorer()


class TestWeightRenormalisation:
    def test_omitting_a_keyword_does_not_penalise(self, scorer):
        """The regression: unmeasured SEO cost 7.5 points."""
        with_keyword = scorer.score_content(WELL_FORMED, keyword="widgets")
        without = scorer.score_content(WELL_FORMED)
        assert "seo" not in without["scores"]
        assert without["overall_score"] >= with_keyword["overall_score"]

    def test_measured_lists_only_what_contributed(self, scorer):
        assert "seo" not in scorer.score_content(WELL_FORMED)["measured"]
        assert "seo" in scorer.score_content(WELL_FORMED, keyword="widgets")["measured"]

    @pytest.mark.parametrize("keyword", [None, "widgets"])
    def test_overall_is_the_weighted_mean_of_measured_dimensions(self, scorer, keyword):
        """
        The invariant the fix establishes: the divisor is the weight of what
        was measured, not the weight of everything that could have been.
        """
        result = scorer.score_content(WELL_FORMED, keyword=keyword)
        measured = result["scores"]
        expected = sum(measured[d] * WEIGHTS[d] for d in measured) / sum(
            WEIGHTS[d] for d in measured
        )
        assert result["overall_score"] == pytest.approx(expected, abs=0.05)

    def test_all_dimensions_at_100_yields_100(self, scorer, monkeypatch):
        """Renormalisation must not cap the achievable maximum below 100."""
        for method in (
            "_score_readability",
            "_score_structure",
            "_score_engagement",
            "_score_completeness",
            "_score_seo",
        ):
            monkeypatch.setattr(
                ContentQualityScorer, method, lambda self, *a, **k: 100.0, raising=True
            )
        assert scorer.score_content("x")["overall_score"] == pytest.approx(100.0)
        assert scorer.score_content("x", keyword="k")["overall_score"] == pytest.approx(100.0)

    def test_every_dimension_has_a_weight(self, scorer):
        result = scorer.score_content(WELL_FORMED, keyword="widgets")
        assert set(result["scores"]) <= set(WEIGHTS)


class TestHeadingCounts:
    def test_h1_is_not_inflated_by_subheadings(self, scorer):
        """count('# ') matched inside '## ' and '### '."""
        assert scorer._score_structure(WELL_FORMED) == 100.0

    def test_two_h1s_lose_the_bonus(self, scorer):
        two = WELL_FORMED + "\n# Second Title\n\nmore\n"
        assert scorer._score_structure(two) < 100.0

    def test_hash_inside_a_line_is_not_a_heading(self, scorer):
        """'issue # 4' is prose, not an H1."""
        text = "Some prose mentioning issue # 4 and a C# example.\n"
        assert scorer._score_structure(text) == 0.0

    def test_structure_can_reach_its_maximum(self, scorer):
        """Components summed to 85 while min(score, 100) implied 100."""
        assert scorer._score_structure(WELL_FORMED) == 100.0

    @pytest.mark.parametrize("marker", ["- item", "* item", "+ item", "1. item"])
    def test_list_markers_are_recognised(self, scorer, marker):
        text = f"# T\n\n## A\n\n## B\n\n## C\n\n### D\n\n### E\n\n{marker}\n"
        assert scorer._score_structure(text) == 100.0


class TestRecommendations:
    def test_weak_engagement_produces_a_recommendation(self, scorer):
        """Previously only readability and structure could produce one."""
        flat = "# T\n\n## A\n\n## B\n\n## C\n\n### D\n\n### E\n\n- x\n\n" + ("plain text. " * 20)
        recs = scorer.score_content(flat)["recommendations"]
        assert any("call to action" in r or "example" in r for r in recs)

    def test_weak_completeness_produces_a_recommendation(self, scorer):
        recs = scorer.score_content("# T\n\nShort.\n")["recommendations"]
        assert any("expand" in r.lower() for r in recs)

    def test_good_content_reports_no_weaknesses(self, scorer):
        long_text = WELL_FORMED + ("widgets are useful. " * 800)
        recs = scorer.score_content(long_text, keyword="widgets")["recommendations"]
        assert recs == ["No weak dimensions; the heuristics are satisfied."]

    def test_recommendations_are_never_empty(self, scorer):
        assert scorer.score_content("# T\n\nx\n")["recommendations"]


class TestEdgeCases:
    def test_empty_content_scores_zero_without_raising(self, scorer):
        result = scorer.score_content("")
        assert result["overall_score"] == 0.0
        assert result["grade"] == "F"

    def test_whitespace_only_is_treated_as_empty(self, scorer):
        assert scorer.score_content("   \n\t ")["overall_score"] == 0.0

    def test_content_with_no_sentence_terminator(self, scorer):
        assert scorer._score_readability("no terminator here") == 0.0

    def test_scores_stay_within_bounds(self, scorer):
        for text in ["", "# T\n", WELL_FORMED, WELL_FORMED * 50]:
            result = scorer.score_content(text, keyword="widgets")
            assert 0.0 <= result["overall_score"] <= 100.0
            for value in result["scores"].values():
                assert 0.0 <= value <= 100.0

    @pytest.mark.parametrize("score,grade", [(95, "A"), (85, "B"), (75, "C"), (65, "D"), (10, "F")])
    def test_grade_boundaries(self, scorer, score, grade):
        assert scorer._get_grade(score) == grade

    def test_keyword_match_is_case_insensitive(self, scorer):
        assert scorer._score_seo("Widgets are great", "widgets") > 0
