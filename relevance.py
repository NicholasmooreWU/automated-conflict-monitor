"""
relevance.py

Single source of truth for "is this article relevant to the conflict/
geopolitical monitor" and "is this article junk that slipped through
NewsAPI's keyword search" (sports recaps, consumer-tech reviews, unrelated
health content, etc.).

Previously this logic existed in two independent places -- a lightweight
keyword check in analyst.py, and a much more elaborate (but hardcoded to a
single region) scoring system in dashboard.py -- which could silently
disagree about the same article. Both analyst.py and dashboard.py should
import score_article() from here instead of keeping their own copy.

Scoring runs in three stages, in this order:

  1. Auto-reject: topic-agnostic noise patterns (sports, consumer-tech
     reviews, unrelated health content, known low-credibility sources).
     These are rejected unless the active run's priority keywords or main
     search keyword appear in the title.
  2. Auto-pass: an explicit mention of the search topic itself (main_keyword)
     or of that topic's "priority keywords" (see REGION_PRIORITY_KEYWORDS in
     dashboard.py). Every region gets this same auto-pass privilege -- none
     is hardcoded as a special case the way "China" used to be.
  3. Secondary scoring: general geopolitical / economic / regional-actor /
     domestic-policy keyword weights, for articles that didn't match #1 or
     #2 but might still be relevant (e.g. a sanctions story that doesn't
     happen to name the region directly).
"""

# ---------------------------------------------------------------------------
# Stage 3: general-purpose relevance keyword categories (topic-agnostic)
# ---------------------------------------------------------------------------
GEOPOLITICAL_KWS = [
    "diplomatic", "sanctions", "military", "conflict", "territorial",
    "sovereignty", "alliance", "strategic", "intelligence", "coercion",
    "provocation", "deterrence", "embargo", "blockade",
]
ECON_TECH_KWS = [
    "tariff", "trade", "chips", "semiconductor", "export controls",
    "supply chain", "rare earth", "currency", "gdp", "investment ban",
    "technology transfer", "dual-use", "ai race", "ev", "clean energy",
]
REGIONAL_ACTORS_KWS = [
    "iran", "taiwan", "philippines", "japan", "india", "russia",
    "north korea", "south korea", "china", "asean", "pacific",
    "indo-pacific", "strait of hormuz", "strait of taiwan",
    "south china sea",
]
DOMESTIC_POLICY_KWS = [
    "censorship", "surveillance", "protest", "crackdown", "propaganda",
    "disinformation", "state media", "communist party", "politburo",
    "social credit", "great firewall",
]

TOPIC_CATEGORY_WEIGHTS = [
    (GEOPOLITICAL_KWS, 0.2),
    (ECON_TECH_KWS, 0.2),
    (REGIONAL_ACTORS_KWS, 0.15),
    (DOMESTIC_POLICY_KWS, 0.1),
]
SCORE_PASS_THRESHOLD = 0.10

# ---------------------------------------------------------------------------
# Stage 1: noise patterns -- topic-agnostic, always checked first
# ---------------------------------------------------------------------------
SPORTS_PATTERN = [
    "review bomb", "review-bomb", "review-bombed", "game update",
    "game patch", "esports", "nba", "nfl", "fifa", "formula 1",
    "snooker", "dlc release", "game studio", "video game",
]
CONSUMER_PRODUCT_PATTERN = [
    "motorcycle review", "best headphones", "buying guide",
    "hands on review", "unboxing", "specs leaked",
    "hits the roads", "hits the road", "looks kind of like",
    "looks like a", "new ioniq", "new iphone", "new pixel",
    "review: ", "first ride", "first drive review",
    "finally hits",
]
HEALTH_UNRELATED_PATTERN = [
    "shingles", "vaccine side effects", "diet tips", "workout",
    "skin care",
]
LOW_CREDIBILITY_SOURCES = [
    "kotaku", "rideapart.com", "guessingheadlines.com",
    "phonearena", "gsmarena", "9to5mac", "9to5google",
    "droid-life", "xda-developers", "phandroid",
    "notebookcheck", "liliputing",
]

RELEVANT_REASONS = {"main_keyword_match", "priority_topic_mention", "scored_pass"}


def is_relevant(reason):
    """Interpret a reason string returned by score_article()."""
    return reason in RELEVANT_REASONS


def _safe_str(val):
    return val if isinstance(val, str) else ""


def _any_keyword_in(text, keywords):
    return any(kw in text for kw in keywords)


def _priority_hit(title_l, body_head_l, priority_keywords):
    if not priority_keywords:
        return False
    return _any_keyword_in(title_l, priority_keywords) or _any_keyword_in(body_head_l, priority_keywords)


def _sports_auto_reject(title_l, body_l, priority_keywords):
    for kw in SPORTS_PATTERN:
        if kw == "snooker":
            if "snooker" in title_l and not _priority_hit(title_l, body_l[:100], priority_keywords):
                return True
            continue
        if (kw in title_l or kw in body_l[:150]) and not _any_keyword_in(title_l, priority_keywords or []):
            return True
    return False


def _consumer_auto_reject(title_l, body_l, priority_keywords):
    for kw in CONSUMER_PRODUCT_PATTERN:
        if (kw in title_l or kw in body_l[:200]) and not _any_keyword_in(title_l, priority_keywords or []):
            return True
    return False


def _health_auto_reject(title_l, body_l, priority_keywords):
    for kw in HEALTH_UNRELATED_PATTERN:
        if kw in title_l and not _priority_hit(title_l, body_l, priority_keywords):
            return True
    return False


def _source_auto_reject(source, title_l, priority_keywords):
    source_l = _safe_str(source).lower().strip()
    if source_l in LOW_CREDIBILITY_SOURCES and not _any_keyword_in(title_l, priority_keywords or []):
        return True
    return False


def _secondary_score(text_l):
    score = 0.0
    for keywords, weight in TOPIC_CATEGORY_WEIGHTS:
        hits = 0
        for kw in keywords:
            if kw in text_l:
                hits += 1
            if hits >= 2:
                break
        score += min(hits, 2) * weight
    return min(score, 1.0)


def score_article(title, body, source="", priority_keywords=None, main_keyword=None):
    """
    Score a single article for relevance.

    priority_keywords: topic-specific auto-pass terms for the CURRENT
        region/query (e.g. a South China Sea run passes ["china", "taiwan",
        "pla ", ...], a Ukraine run passes ["ukraine", "russia", "putin",
        ...]). This replaces the old hardcoded China-only auto-pass path --
        every region gets the same auto-pass privilege China used to get
        alone.
    main_keyword: the literal search query used to fetch this article. An
        explicit match is always treated as an auto-pass.

    Returns (score: float in [0, 1], reason: str). Use is_relevant(reason)
    to interpret the result rather than hardcoding reason strings at call
    sites.
    """
    title_l = _safe_str(title).lower()
    body_l = _safe_str(body).lower()
    combined = f"{title_l} {body_l}"

    if main_keyword and main_keyword.lower() in combined:
        return 1.0, "main_keyword_match"

    if _sports_auto_reject(title_l, body_l, priority_keywords):
        return 0.0, "auto_reject_sports"
    if _consumer_auto_reject(title_l, body_l, priority_keywords):
        return 0.0, "auto_reject_consumer"
    if _health_auto_reject(title_l, body_l, priority_keywords):
        return 0.0, "auto_reject_health"
    if _source_auto_reject(source, title_l, priority_keywords):
        return 0.0, "auto_reject_low_credibility_source"

    if _priority_hit(title_l, body_l[:300], priority_keywords):
        return 1.0, "priority_topic_mention"

    score = _secondary_score(combined)
    if score >= SCORE_PASS_THRESHOLD:
        return score, "scored_pass"
    return score, "failed_secondary_scoring"