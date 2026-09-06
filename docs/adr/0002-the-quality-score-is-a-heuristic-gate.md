# ADR 0002 — The quality score is a heuristic first-pass filter, and it says so

**Status:** accepted · **Date:** 2026-09-06 (records the decision made in PR #1)

## Context

`quality_scorer.py` grades generated articles out of 100 across readability,
structure, engagement, SEO and completeness. The UI called it a "100-point
audit". Four defects made the number wrong before the question of what it
measures could even be asked:

- With no keyword supplied, `seo` was scored 0 and its 0.15 weight still
  applied, so identical content lost 7.5 points for not being given a keyword.
- `content.count("# ")` also matches inside `"## "` and `"### "`, so a document
  with three subheadings counted at least three H1s and the "exactly one H1"
  bonus was unreachable for every document the pipeline produces.
- The structure components summed to 85 while the function ended in
  `min(score, 100)`, implying 100 was attainable.
- Recommendations covered two dimensions; the other three could score zero and
  produce "Content looks great!".

## Decision

1. Weights are renormalised over the dimensions actually measured, headings are
   matched at line starts, structure's components total 100, and every
   dimension can produce a recommendation. Twenty tests pin this.
2. The scorer stays deliberately heuristic — regular expressions over the text,
   no model call — and is described as a cheap first-pass filter, not a
   judgement of quality. It runs after generation to give the operator a
   structured look at the draft; it does not gate publication, because nothing
   here publishes.
3. Numbers it produces are shown with the dimension they came from. The UI's
   invented "Complexity Index: High" was removed; the two remaining metrics are
   counts from the run.

## Consequences

- The grade is reproducible and explainable: the same text always scores the
  same, and each recommendation names the dimension that triggered it.
- It cannot detect fabrication, plagiarism or factual error. The crew's
  fact-checker agent is a model prompt with a web search tool, and is described
  as such in the README; a human still has to read the article.
- Changing a weight changes every historical grade; the version table stores
  article text, not grades, for that reason.
