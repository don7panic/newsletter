"""AI scoring and summarization client for newsletter items.

Uses an OpenAI-compatible API to score (0-10) and summarize each item.
Scores are used internally for filtering; only summaries are exposed in output.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from newsletter import config

LOGGER = logging.getLogger(__name__)

_ANALYSIS_SYSTEM_PROMPT = """You are an expert content curator helping filter important technical information.

Score content on a 0-10 scale based on importance and relevance:

**9-10: Groundbreaking** — Major breakthroughs, paradigm shifts, or highly significant announcements
- New major version releases of widely-used technologies
- Significant research breakthroughs
- Important industry-changing announcements

**7-8: High Value** — Important developments worth immediate attention
- Interesting technical deep-dives
- Novel approaches to known problems
- Insightful analysis or commentary
- Valuable tools or libraries

**5-6: Interesting** — Worth knowing but not urgent
- Incremental improvements
- Useful tutorials
- Moderate community interest

**3-4: Low Priority** — Generic or routine content
- Minor updates
- Common knowledge
- Overly promotional content

**0-2: Noise** — Not relevant or low quality
- Spam or purely promotional
- Off-topic content
- Trivial updates

Consider: technical depth, novelty, potential impact, quality of writing, relevance to software engineering and technology.
"""

_ANALYSIS_USER_PROMPT = """Analyze the following content and provide a JSON response with:
- score (0-10): Importance score following the rubric
- reason: Brief explanation for the score
- summary: One-sentence summary of the content

Title: {title}
Source: {source}
Summary: {summary}
Metadata: {meta}

Respond with valid JSON only:
{{"score": <number>, "reason": "<explanation>", "summary": "<one-sentence-summary>"}}"""


def _make_client() -> OpenAI:
    return OpenAI(
        api_key=config.AI_API_KEY,
        base_url=config.AI_BASE_URL,
    )


def _call_ai(client: OpenAI, item: dict) -> dict[str, Any] | None:
    meta = item.get("meta", {})
    meta_str = json.dumps(meta, ensure_ascii=False)

    try:
        response = client.chat.completions.create(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": _ANALYSIS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _ANALYSIS_USER_PROMPT.format(
                        title=item.get("title", ""),
                        source=item.get("source", ""),
                        summary=item.get("summary", ""),
                        meta=meta_str,
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=1024,
        )
    except Exception as exc:
        LOGGER.debug("AI call failed for item '%s': %s", item.get("title", ""), exc)
        return None

    raw = response.choices[0].message.content
    if not raw:
        LOGGER.debug("AI returned empty response for item '%s'", item.get("title", ""))
        return None

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        LOGGER.debug("AI returned invalid JSON for item '%s': %s", item.get("title", ""), raw[:100])
        return None

    return result


def score_and_summarize(items: list[dict]) -> tuple[list[dict], bool]:
    """Score and summarize each item using AI.

    Each item is enriched with ``ai_score`` (float) and ``ai_summary`` (str).
    If the AI call fails for an item, it receives a default score of 5.0 and
    keeps its original summary, ensuring the pipeline never breaks.

    Args:
        items: List of item dicts from fetchers.

    Returns:
        Tuple of (enriched items, ai_worked). ``ai_worked`` is True if at
        least one AI call succeeded.
    """
    if not items:
        return [], False

    client = _make_client()
    scored: list[dict] = []
    any_succeeded = False

    for item in items:
        result = _call_ai(client, item)
        if result is None:
            item["ai_score"] = 5.0
            item["ai_summary"] = item.get("summary", "")
        else:
            item["ai_score"] = float(result.get("score", 5.0))
            item["ai_summary"] = result.get("summary", item.get("summary", ""))
            any_succeeded = True

        scored.append(item)

    return scored, any_succeeded