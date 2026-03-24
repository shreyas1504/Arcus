# ── backend/routers/news.py ────────────────────────────────────────────────
# Market news from live RSS feeds — no API key needed.

import time
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter

logger = logging.getLogger("pulse.news")

router = APIRouter(prefix="/api/news", tags=["news"])

# ── In-memory cache ──────────────────────────────────────────────────────────
_news_cache: dict[str, tuple[float, list]] = {}
_NEWS_CACHE_TTL = 300  # 5 minutes

# RSS feeds — free, no API key
RSS_FEEDS = [
    {"url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=&region=US&lang=en-US", "source": "Yahoo Finance"},
    {"url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "source": "CNBC"},
    {"url": "https://feeds.marketwatch.com/marketwatch/topstories/", "source": "MarketWatch"},
    {"url": "https://feeds.reuters.com/reuters/businessNews", "source": "Reuters"},
]

TICKER_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


def _parse_rss_datetime(dt_str: str) -> int:
    """Parse RSS date string to unix timestamp."""
    try:
        dt = parsedate_to_datetime(dt_str)
        return int(dt.timestamp())
    except Exception:
        try:
            # Try ISO format
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except Exception:
            return int(time.time())


def _fetch_single_feed(feed: dict) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    import urllib.request

    try:
        req = urllib.request.Request(
            feed["url"],
            headers={"User-Agent": "Mozilla/5.0 (Pulse Portfolio Analytics)"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            xml_data = response.read().decode("utf-8", errors="replace")

        root = ET.fromstring(xml_data)
        articles = []

        # Standard RSS 2.0
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "#").strip()
            desc = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "")

            if not title or title.startswith("<?"):
                continue

            # Clean HTML from description
            desc = desc.replace("<![CDATA[", "").replace("]]>", "")
            if "<" in desc:
                # Strip HTML tags
                import re
                desc = re.sub(r"<[^>]+>", "", desc)
            desc = desc[:200].strip()

            articles.append({
                "headline": title,
                "source": feed["source"],
                "url": link,
                "summary": desc,
                "datetime": _parse_rss_datetime(pub_date) if pub_date else int(time.time()),
            })

        return articles[:8]  # Max 8 per feed
    except Exception as e:
        logger.warning(f"RSS feed error ({feed['source']}): {e}")
        return []


def _fetch_all_feeds() -> list[dict]:
    """Fetch all RSS feeds in parallel."""
    all_articles: list[dict] = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_fetch_single_feed, feed): feed for feed in RSS_FEEDS}
        for future in as_completed(futures, timeout=15):
            try:
                articles = future.result()
                all_articles.extend(articles)
            except Exception:
                pass

    # Sort by datetime (newest first), deduplicate by headline
    seen = set()
    unique = []
    for article in sorted(all_articles, key=lambda x: x["datetime"], reverse=True):
        h = article["headline"].lower()[:60]
        if h not in seen:
            seen.add(h)
            article["id"] = str(hash(h))[:12]
            article["category"] = "general"
            unique.append(article)

    return unique[:20]


def _fetch_ticker_feed(ticker: str) -> list[dict]:
    """Fetch news for a specific ticker via Yahoo Finance RSS."""
    feed = {"url": TICKER_RSS.format(ticker=ticker), "source": "Yahoo Finance"}
    articles = _fetch_single_feed(feed)
    for a in articles:
        a["related"] = ticker
        a["id"] = str(hash(a["headline"].lower()[:60]))[:12]
    return articles


@router.get("/market")
def get_market_news():
    """Get rolling market news from live RSS feeds."""
    cache_key = "market"
    if cache_key in _news_cache:
        cached_time, cached_data = _news_cache[cache_key]
        if time.time() - cached_time < _NEWS_CACHE_TTL:
            return {"news": cached_data}

    news = _fetch_all_feeds()

    # Fallback to mock if all feeds fail
    if not news:
        news = _mock_fallback()

    _news_cache[cache_key] = (time.time(), news)
    return {"news": news}


@router.get("/ticker/{ticker}")
def get_ticker_news(ticker: str):
    """Get news for a specific ticker."""
    ticker = ticker.upper()
    cache_key = f"ticker_{ticker}"
    if cache_key in _news_cache:
        cached_time, cached_data = _news_cache[cache_key]
        if time.time() - cached_time < _NEWS_CACHE_TTL:
            return {"ticker": ticker, "news": cached_data}

    news = _fetch_ticker_feed(ticker)
    _news_cache[cache_key] = (time.time(), news)
    return {"ticker": ticker, "news": news}


def _mock_fallback() -> list[dict]:
    """Last-resort mock data if RSS feeds are all down."""
    now = int(time.time())
    return [
        {"id": "1", "headline": "Markets update — checking live feeds...", "source": "Pulse", "url": "#",
         "summary": "Live RSS feeds are temporarily unavailable. News will refresh automatically.", "datetime": now, "category": "general"},
    ]


@router.get("/sentiment/{ticker}")
def get_ticker_sentiment(ticker: str):
    """Analyze sentiment of recent headlines for a ticker using VADER."""
    ticker = ticker.upper()
    cache_key = f"sentiment_{ticker}"
    if cache_key in _news_cache:
        cached_time, cached_data = _news_cache[cache_key]
        if time.time() - cached_time < _NEWS_CACHE_TTL:
            return cached_data

    # Fetch headlines
    news = _fetch_ticker_feed(ticker)
    headlines = [a["headline"] for a in news if a.get("headline")]

    if not headlines:
        result = {"ticker": ticker, "score": 0.0, "label": "NEUTRAL", "confidence": 0.0, "headline_count": 0}
        _news_cache[cache_key] = (time.time(), result)
        return result

    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
        analyzer = SentimentIntensityAnalyzer()
        scores = [analyzer.polarity_scores(h)["compound"] for h in headlines]
    except ImportError:
        # Fallback: simple keyword-based sentiment if VADER not installed
        positive_words = {"surge", "gain", "rally", "jump", "soar", "rise", "bull", "high", "record", "growth", "profit", "beat", "upgrade"}
        negative_words = {"drop", "fall", "crash", "plunge", "loss", "bear", "low", "decline", "miss", "downgrade", "cut", "fear", "risk", "sell"}
        scores = []
        for h in headlines:
            words = set(h.lower().split())
            pos = len(words & positive_words)
            neg = len(words & negative_words)
            total = pos + neg
            scores.append((pos - neg) / max(total, 1))

    avg = sum(scores) / len(scores) if scores else 0.0
    label = "BULLISH" if avg > 0.05 else "BEARISH" if avg < -0.05 else "NEUTRAL"
    confidence = round(min(abs(avg) * 2, 1.0), 3)

    result = {
        "ticker": ticker,
        "score": round(avg, 4),
        "label": label,
        "confidence": confidence,
        "headline_count": len(headlines),
    }
    _news_cache[cache_key] = (time.time(), result)
    return result
