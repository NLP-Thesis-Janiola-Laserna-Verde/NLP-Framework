# Annotation Guidelines and Rating Form: Source Suitability (0–3)

Draft v0.1 · November 10, 2026 · Multi-Signal NLP Framework for Ranking Online Sources (SP 198)

## 1. Purpose

This document tells annotators how to judge whether an online source is **suitable to cite for academic research on a given topic**. Your ratings become the human-labeled ground truth used to evaluate the ranking framework (Precision@k, Recall@k, NDCG@k, MAP) and to check how well its rankings agree with human judgment.

You are not rating how interesting a source is, how well it is written, or whether its claims are true. You are rating whether a researcher could reasonably use it as a citation for the stated topic.

## 2. What you will receive

For each topic you get a short topic statement and a list of candidate sources (title and URL). Sources are shown in random order, with **no system scores, ranks, or retrieval source shown**. Do not try to find out how the system ranked them.

## 3. Ground rules

- Open each URL and look at the actual page. Do not rate from the title or search snippet alone.
- Judge each source on its own. Do not compare it with the other candidates for the topic.
- Check the publisher outside the page when you are unsure who they are (open a new tab and see what other sites say about them; this is lateral reading). Do not trust the page's description of itself.
- Do not use AI chatbots to rate or summarize sources. Search engines and journal or publisher websites are fine.
- Rate independently. Do not discuss ratings with other annotators until the calibration meeting.
- Spend about 3–5 minutes per source. If a page cannot be opened or read, use the flags in Section 6 and do not guess.
- Accuracy is out of scope. You do not need to fact-check claims. If something looks clearly false or fabricated, flag it and say why in the notes.

## 4. The five ratings

Every source gets five ratings on a 0–3 scale. Rate the four sub-ratings first, then give the overall suitability.

### 4.1 Topical relevance (R)

| Score | Meaning |
| --- | --- |
| 3 | Directly and substantially addresses the topic. Most of the source is about it. |
| 2 | Addresses the topic in part, or is somewhat broader or narrower than the topic. Useful for a section of a paper. |
| 1 | Only tangentially related. The topic is mentioned briefly or appears as background. |
| 0 | Not about the topic, or the overlap is only in keywords. |

### 4.2 Authority (A)

Who published it, and is that publisher a recognized, accountable source on this kind of subject?

| Score | Meaning |
| --- | --- |
| 3 | Peer-reviewed work in an established venue, or published by a government agency, university, research institute, or recognized international organization. |
| 2 | Reputable organization or publisher, but not peer-reviewed or not clearly expert in this subject (for example, a professional body's magazine, a well-known industry research group). |
| 1 | Publisher or author has limited or unclear expertise, or the page does not clearly say who is responsible. An .org domain with no clear reputation belongs here. |
| 0 | Anonymous, unverifiable, or purely commercial or personal publisher. |

A domain such as .gov, .edu, or .org is a hint, not a verdict. Check who is actually behind the page.

### 4.3 Currency (C)

Is the source recent enough for this topic? Judge against how fast the topic changes. For fast-moving topics (for example, large language models), a source from several years ago may be outdated. For slow-moving or foundational topics, an older source may still be the right one to cite.

| Score | Meaning |
| --- | --- |
| 3 | Current for the topic, or a foundational or landmark work that is still standard to cite. |
| 2 | Somewhat dated, but its content still holds for the topic. |
| 1 | Likely outdated for the topic, or no publication date can be found (also add the NO\_DATE flag). |
| 0 | Clearly obsolete for the topic. |

Use the original publication date. A "last updated" date alone does not make an old source current.

### 4.4 Purpose and genre (P)

What kind of text is it, and is that kind of text appropriate to cite in academic work?

| Score | Meaning |
| --- | --- |
| 3 | Research article, preprint, thesis, institutional or technical report, white paper, standard, or official documentation. |
| 2 | Reputable informative secondary source, such as an encyclopedia entry, a news article from an established outlet, or a university explainer. Fine as background, weaker as a primary citation. |
| 1 | Mixed or unclear: informative content that is promotional, strongly opinionated, or a thin summary of someone else's work. |
| 0 | Personal blog, forum or Q&A thread, social media post, opinion piece, marketing or product page, or content-farm article. |

### 4.5 Overall suitability (S): the main label

Given the topic, would you be comfortable citing this source in an academic paper on it? Weigh the four ratings above, but make a judgment. Do not just average them.

| Score | Label | Meaning |
| --- | --- | --- |
| 3 | Highly suitable | On topic, credible, appropriate genre, and suitably current. You would cite it without hesitation. |
| 2 | Suitable | Good overall with one clear weakness (somewhat dated, partly off-focus, or a secondary source). You would cite it, perhaps with a caveat. |
| 1 | Marginal | Related, but with weaknesses that would make you hesitate. You would use it for background or as a lead to better sources, not as a main citation. |
| 0 | Not suitable | Off topic, or an inappropriate or unverifiable source. You would not cite it. |

**Consistency rules for S:**

1. S can never be higher than R. An off-topic source (R = 0) gets S = 0, however credible it is.
2. If P = 0 (blog, forum, opinion, marketing), S is at most 1.
3. If A = 0, S is at most 1.
4. If C = 0, S is at most 1.

## 5. Worked examples

The examples below are illustrative. Replace them with real examples from your pilot topics during calibration.

| Topic | Source | R | A | C | P | S | Why |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Effects of microplastics on freshwater fish | Peer-reviewed review article in an established environmental science journal, published 2 years ago | 3 | 3 | 3 | 3 | 3 | Direct, credible, current, scholarly. |
| Effects of microplastics on freshwater fish | Government environment agency report on microplastics in rivers, 8 years ago | 2 | 3 | 1 | 3 | 2 | Credible and relevant, but dated for a fast-moving topic. Fish effects are only part of it. |
| Effects of microplastics on freshwater fish | Personal blog post summarizing "five scary facts" about microplastics | 2 | 0 | 2 | 0 | 1 | On topic, but a blog. Capped at 1 by the genre rule. |
| Effects of microplastics on freshwater fish | Peer-reviewed paper on microplastics in soil | 1 | 3 | 3 | 3 | 1 | Credible but only tangential to the topic. |
| Effects of microplastics on freshwater fish | Online store page for water filters mentioning microplastics | 0 | 0 | 2 | 0 | 0 | Off topic and commercial. |

## 6. Edge cases and flags

Use these decisions so annotators treat common cases the same way.

- **Source cannot be opened (broken link, error page):** leave the ratings blank and set the DEAD\_LINK flag.
- **Paywalled or login required:** if the abstract or enough content is visible to rate it, rate it and set PAYWALL. Otherwise leave blank and set PAYWALL.
- **Not in English:** leave blank and set NON\_ENGLISH (the study scope is English-language text).
- **Mostly video, images, or slides with no usable text:** leave blank and set NON\_TEXT.
- **Duplicate of another candidate (same work at a different URL):** rate both normally and set DUPLICATE.
- **No publication date found:** C = 1 and set NO\_DATE.
- **Preprint:** not peer-reviewed, but scholarly. A = 2 or 3 depending on the server and authors. P = 3.
- **Wikipedia or similar encyclopedia:** A = 1 or 2, P = 2. Useful for background, so S is usually 1 or 2.
- **Reputable news article about a study:** P = 2. Prefer rating the news piece as it is, not the underlying study.
- **Source looks fabricated or clearly false:** rate as usual, set SUSPECT, and explain in the notes.
- **Unsure between two scores:** pick the lower one and write one line in the notes about what made you hesitate.

## 7. Rating form

One row per (annotator, topic, source). Use a spreadsheet or form that exports to CSV with exactly these columns so it can be loaded straight into the pipeline.

| Column | Type | Notes |
| --- | --- | --- |
| annotator\_id | text | Anonymous ID such as A1, A2, A3 |
| topic\_id | text | From the topic list |
| source\_id | text | From the candidate list |
| url | text | Pre-filled |
| title | text | Pre-filled |
| relevance\_R | 0–3 | Section 4.1 |
| authority\_A | 0–3 | Section 4.2 |
| currency\_C | 0–3 | Section 4.3 |
| purpose\_P | 0–3 | Section 4.4 |
| suitability\_S | 0–3 | Section 4.5, the main label |
| source\_type | dropdown | journal article, preprint, thesis, institutional report, white paper, government page, university page, news, encyclopedia, blog, forum or Q&A, social media, commercial page, other |
| flags | multi-select | DEAD\_LINK, PAYWALL, NON\_ENGLISH, NON\_TEXT, DUPLICATE, NO\_DATE, SUSPECT |
| time\_spent\_min | number | Optional, helps check workload |
| notes | text | Required when S is 1 or unsure, and for any flag |

A source that is flagged and left blank is excluded from the ground truth for that annotator.

## 8. Quality control

1. **Calibration meeting.** Before the pilot, all annotators read this document together and rate 3 shared sources out loud to align on the scales.
2. **Pilot (5 topics).** Every annotator rates the same candidate sources for the 5 pilot topics. Compute agreement on S (quadratic weighted Cohen's kappa for two annotators, or Krippendorff's alpha for three or more, treating the scale as ordinal). Review every pair that differs by 2 or more points.
3. **Revise.** Update the wording, examples, and edge cases based on the disagreements, then record the version number.
4. **Main annotation (50 topics).** Each source is rated by at least two annotators. Re-check a random sample of about 10% for drift.
5. **Final label.** If two annotators differ by 1 point, use the mean or a discussion to settle. If they differ by 2 or more, resolve in discussion. Record the rule you choose before looking at any system results.

## 9. Notes for the team

- The form deliberately does not ask annotators to look up SJR quartile. That keeps the human labels independent of the signals the system uses, so the comparison is fair. Annotators judge authority by who the publisher is and how they are regarded.
- The four sub-ratings are for analysis (they help explain where the system and humans disagree, and support the ablation discussion). The primary ground truth for Precision@k, Recall@k, NDCG@k, and MAP is suitability\_S.
- For binary metrics such as Precision@k and Recall@k, decide the relevance threshold before annotating (for example, S ≥ 2 counts as suitable) and state it in the methodology.
- Fill in the \[number of annotators\], \[number of candidate sources per topic\], and the pilot agreement target (a common target is a weighted kappa of about 0.6 to 0.7 or higher) once the team agrees on them.
