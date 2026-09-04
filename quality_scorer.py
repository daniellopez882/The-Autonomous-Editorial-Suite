"""
quality_scorer.py
Heuristic quality scoring for generated content.

Four defects are fixed here.

1. **Unmeasured dimensions were still scored.** When no keyword was supplied,
   ``seo`` was set to 0 and its 0.15 weight applied anyway, so identical
   content lost 7.5 points purely for not being given a keyword. Weights are
   now renormalised over the dimensions actually measured.

2. **Heading counts were wrong.** ``content.count("# ")`` also matches inside
   ``"## "`` and ``"### "``, because those contain the substring. A document
   with three ``##`` headings counted at least three H1s, so the
   ``h1_count == 1`` bonus was unreachable for any document that had
   subheadings -- which is every document the pipeline produces. Headings are
   now matched at line starts.

3. **Structure could never reach its stated maximum.** The components summed
   to 85, yet the function ended in ``min(score, 100)``, implying 100 was
   attainable. Weights now total 100.

4. **Recommendations only covered two dimensions.** ``engagement``, ``seo`` and
   ``completeness`` could score zero and produce "Content looks great!".

The scoring remains deliberately heuristic: it is a cheap first-pass filter,
not a judgement of quality. See ``score_content``'s docstring for what that
means for callers.
"""

from __future__ import annotations

import re

# Relative importance of each dimension. Renormalised at scoring time over
# whichever dimensions were actually measured.
WEIGHTS: dict[str, float] = {
    "readability": 0.25,
    "structure": 0.20,
    "engagement": 0.25,
    "seo": 0.15,
    "completeness": 0.15,
}

GRADE_BOUNDARIES: tuple[tuple[float, str], ...] = (
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
)

RECOMMENDATIONS: dict[str, str] = {
    "readability": "Shorten sentences; aim for an average under 20 words.",
    "structure": "Add a single H1 and at least three H2 sections.",
    "engagement": "Add a question, a concrete example, and a call to action.",
    "seo": "Work the target keyword into the copy and expand past 1000 words.",
    "completeness": "The piece is short; expand it past 1000 words.",
}

# Heading counted only at the start of a line, optionally indented.
_H1 = re.compile(r"^[ \t]{0,3}#(?!#)\s+\S", re.MULTILINE)
_H2 = re.compile(r"^[ \t]{0,3}##(?!#)\s+\S", re.MULTILINE)
_H3 = re.compile(r"^[ \t]{0,3}###(?!#)\s+\S", re.MULTILINE)
_LIST = re.compile(r"^[ \t]{0,3}(?:[-*+]\s+|\d+\.\s+)\S", re.MULTILINE)
_SENTENCE_END = re.compile(r"[.!?]+")

CTA_PHRASES = ("learn more", "get started", "try ", "discover", "sign up", "read more")


class ContentQualityScorer:
    """Score content across five heuristic dimensions."""

    def score_content(self, content: str, keyword: str | None = None) -> dict:
        """
        Score a piece of content.

        Dimensions that cannot be measured are omitted rather than scored zero,
        and the remaining weights are renormalised. ``measured`` lists what
        actually contributed, so a caller can see whether a low score reflects
        the content or a missing input.

        The result is a heuristic: it counts headings, sentence lengths and
        keyword presence. It does not assess whether the content is accurate,
        original or useful.
        """
        if not content or not content.strip():
            return {
                "overall_score": 0.0,
                "scores": {},
                "measured": [],
                "grade": "F",
                "recommendations": ["No content to score."],
            }

        scores: dict[str, float] = {
            "readability": self._score_readability(content),
            "structure": self._score_structure(content),
            "engagement": self._score_engagement(content),
            "completeness": self._score_completeness(content),
        }
        if keyword:
            scores["seo"] = self._score_seo(content, keyword)

        total_weight = sum(WEIGHTS[dimension] for dimension in scores)
        overall = sum(scores[d] * WEIGHTS[d] for d in scores) / total_weight

        return {
            "overall_score": round(overall, 1),
            "scores": scores,
            "measured": sorted(scores),
            "grade": self._get_grade(overall),
            "recommendations": self._get_recommendations(scores),
        }

    # ---------------------------------------------------------- dimensions
    def _score_readability(self, content: str) -> float:
        sentences = len(_SENTENCE_END.findall(content))
        words = len(content.split())
        if sentences == 0 or words == 0:
            return 0.0
        average = words / sentences
        if average <= 15:
            return 100.0
        if average <= 20:
            return 80.0
        if average <= 25:
            return 60.0
        return 40.0

    def _score_structure(self, content: str) -> float:
        """
        Heading structure.

        Counts are line-anchored: ``content.count("# ")`` also matched the "# "
        inside "## " and "### ", so H1s were over-counted by every subheading
        present and the "exactly one H1" bonus was unreachable.

        Components sum to 100 so the maximum is actually attainable.
        """
        score = 0.0
        if len(_H1.findall(content)) == 1:
            score += 25
        if len(_H2.findall(content)) >= 3:
            score += 35
        if len(_H3.findall(content)) >= 2:
            score += 20
        if _LIST.search(content):
            score += 20
        return min(score, 100.0)

    def _score_engagement(self, content: str) -> float:
        lowered = content.lower()
        score = 0.0
        if "?" in content:
            score += 20
        if "example" in lowered:
            score += 20
        if re.search(r"\d", content):
            score += 20
        if '"' in content or "“" in content:
            score += 15
        if any(phrase in lowered for phrase in CTA_PHRASES):
            score += 25
        return min(score, 100.0)

    def _score_seo(self, content: str, keyword: str) -> float:
        if not keyword:
            return 0.0
        score = 0.0
        if keyword.lower() in content.lower():
            score += 50
        if len(content.split()) >= 1000:
            score += 50
        return min(score, 100.0)

    def _score_completeness(self, content: str) -> float:
        words = len(content.split())
        if words >= 1500:
            return 100.0
        if words >= 1000:
            return 80.0
        if words >= 500:
            return 60.0
        return 40.0

    # ------------------------------------------------------------- output
    def _get_grade(self, score: float) -> str:
        for boundary, grade in GRADE_BOUNDARIES:
            if score >= boundary:
                return grade
        return "F"

    def _get_recommendations(self, scores: dict) -> list[str]:
        """One recommendation per weak dimension, for every dimension scored."""
        weak = [
            RECOMMENDATIONS[dimension]
            for dimension, value in sorted(scores.items(), key=lambda kv: kv[1])
            if value < 70 and dimension in RECOMMENDATIONS
        ]
        return weak or ["No weak dimensions; the heuristics are satisfied."]
