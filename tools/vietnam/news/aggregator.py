
from dexter_vietnam.tools.base import BaseTool
from typing import Dict, Any, Optional, List
from datetime import datetime
import re
import logging

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

# RSS feeds theo category
RSS_FEEDS = {
    "market": [
        ("CafeF",     "https://cafef.vn/thi-truong-chung-khoan.rss"),
        ("VnExpress", "https://vnexpress.net/rss/kinh-doanh/chung-khoan.rss"),
    ],
    "business": [
        ("CafeF",     "https://cafef.vn/doanh-nghiep.rss"),
        ("VnExpress", "https://vnexpress.net/rss/kinh-doanh/doanh-nghiep.rss"),
    ],
    "macro": [
        ("CafeF",     "https://cafef.vn/vi-mo-dau-tu.rss"),
        ("VnExpress", "https://vnexpress.net/rss/kinh-doanh.rss"),
    ],
    "home": [
        ("CafeF",     "https://cafef.vn/home.rss"),
        ("VnExpress", "https://vnexpress.net/rss/kinh-doanh.rss"),
    ],
}

# Tất cả feeds gom lại (dùng cho latest / search / stock_news)
ALL_FEEDS = [
    ("CafeF",     "https://cafef.vn/home.rss"),
    ("CafeF",     "https://cafef.vn/thi-truong-chung-khoan.rss"),
    ("CafeF",     "https://cafef.vn/doanh-nghiep.rss"),
    ("VnExpress", "https://vnexpress.net/rss/kinh-doanh.rss"),
]


class NewsAggregatorTool(BaseTool):

    REQUEST_TIMEOUT = 10  # seconds

    def __init__(self):
        if requests is None or BeautifulSoup is None:
            raise ImportError(
                "requests and beautifulsoup4 are required. "
                "Install with: pip install requests beautifulsoup4 lxml"
            )

    def get_name(self) -> str:
        return "news_aggregator"

    def get_description(self) -> str:
        return (
            "Thu thập tin tức chứng khoán Việt Nam qua RSS từ CafeF, VnExpress. "
            "Tìm kiếm theo mã cổ phiếu hoặc từ khoá."
        )

    def get_actions(self) -> dict:
        return {
            "latest":     "Tin tức mới nhất từ tất cả nguồn RSS",
            "stock_news": "Tin tức cho 1 mã cổ phiếu (lọc theo symbol trong tiêu đề/mô tả)",
            "market":     "Tin tức thị trường chứng khoán",
            "search":     "Tìm kiếm tin theo từ khoá (keyword trong params)",
        }

    async def run(self, symbol: str = "", action: str = "latest", **kwargs) -> Dict[str, Any]:
        action_map = {
            "latest":     self._get_latest_news,
            "search":     self._search_news,
            "stock_news": self._get_stock_news,
            "market":     self._get_market_news,
        }
        if action not in action_map:
            return {"success": False, "error": f"Action không hợp lệ: {action}. Dùng: {list(action_map.keys())}"}
        try:
            return await action_map[action](symbol, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _fetch_rss(self, url: str) -> Optional["BeautifulSoup"]:
        """Lấy và parse RSS feed."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return BeautifulSoup(resp.text, "lxml-xml")
        except Exception as e:
            logger.warning(f"Lỗi fetch RSS {url}: {e}")
            return None

    def _parse_rss_feed(self, source_name: str, url: str, limit: int = 20) -> List[Dict]:
        """Parse 1 RSS feed → list of article dicts."""
        soup = self._fetch_rss(url)
        if not soup:
            return []

        articles = []
        for item in soup.find_all("item")[:limit]:
            title = self._text(item.find("title"))
            if not title or len(title) < 10:
                continue

            link = self._extract_link(item)
            pub_date = self._text(item.find("pubDate") or item.find("pubdate"))
            description = self._extract_description(item)

            articles.append({
                "title":     title,
                "url":       link,
                "source":    source_name,
                "published": pub_date,
                "summary":   description,
            })
        return articles

    def _parse_feeds(self, feeds: List[tuple], limit_per_feed: int = 20) -> List[Dict]:
        """Parse nhiều feeds, gộp lại và deduplicate theo title."""
        all_articles = []
        seen_titles = set()

        for source_name, url in feeds:
            items = self._parse_rss_feed(source_name, url, limit_per_feed)
            for item in items:
                key = item["title"].strip().lower()[:60]
                if key not in seen_titles:
                    seen_titles.add(key)
                    all_articles.append(item)

        return all_articles


    def _text(self, tag) -> str:
        if tag is None:
            return ""
        return re.sub(r"\s+", " ", tag.get_text() or "").strip()

    def _extract_link(self, item) -> str:
        """Lấy URL từ <link> tag trong RSS (nhiều format khác nhau)."""
        link_tag = item.find("link")
        if not link_tag:
            return ""
        # Format 1: text content
        text = (link_tag.string or "").strip()
        if text.startswith("http"):
            return text
        # Format 2: next sibling (CDATA)
        sibling = link_tag.next_sibling
        if sibling and str(sibling).strip().startswith("http"):
            return str(sibling).strip()
        # Format 3: href attribute
        return link_tag.get("href", "")

    def _extract_description(self, item) -> str:
        """Lấy description và strip HTML tags."""
        desc_tag = item.find("description")
        if not desc_tag:
            return ""
        raw = desc_tag.get_text()
        # Strip HTML nếu có
        try:
            soup = BeautifulSoup(raw, "lxml")
            text = soup.get_text()
        except Exception:
            text = raw
        return re.sub(r"\s+", " ", text).strip()[:300]

    def _filter_by_keyword(self, articles: List[Dict], keyword: str) -> List[Dict]:
        """Lọc danh sách bài viết theo keyword (tìm trong title + summary)."""
        kw = keyword.upper()
        return [
            a for a in articles
            if kw in (a.get("title", "") + " " + a.get("summary", "")).upper()
        ]



    async def _get_latest_news(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Tin mới nhất từ tất cả nguồn RSS."""
        limit = kwargs.get("limit", 15)
        source = kwargs.get("source", "all")

        feeds = self._select_feeds(source, "home")
        articles = self._parse_feeds(feeds, limit_per_feed=limit)

        if symbol:
            filtered = self._filter_by_keyword(articles, symbol)
            if filtered:
                articles = filtered

        articles = articles[:limit]

        return {
            "success": True,
            "report":  "latest_news",
            "source":  source,
            "count":   len(articles),
            "data":    articles,
        }

    async def _get_stock_news(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Tin tức liên quan đến 1 mã cổ phiếu (lọc keyword trong title/summary)."""
        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        limit = kwargs.get("limit", 10)
        source = kwargs.get("source", "all")

        feeds = self._select_feeds(source, "home")
        # Cũng lấy thêm từ market + business feeds để tăng coverage
        extra = self._select_feeds(source, "market") + self._select_feeds(source, "business")
        all_feeds = list({url: (name, url) for name, url in feeds + extra}.values())

        articles = self._parse_feeds(all_feeds, limit_per_feed=30)
        filtered = self._filter_by_keyword(articles, symbol)
        filtered = filtered[:limit]

        return {
            "success": True,
            "report":  "stock_news",
            "symbol":  symbol.upper(),
            "count":   len(filtered),
            "data":    filtered,
        }

    async def _get_market_news(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Tin thị trường và vĩ mô."""
        limit    = kwargs.get("limit", 15)
        source   = kwargs.get("source", "all")
        category = kwargs.get("category", "market")  # market | business | macro

        feeds = self._select_feeds(source, category if category in RSS_FEEDS else "market")
        articles = self._parse_feeds(feeds, limit_per_feed=limit)
        articles = articles[:limit]

        return {
            "success":  True,
            "report":   "market_news",
            "category": category,
            "count":    len(articles),
            "data":     articles,
        }

    async def _search_news(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Tìm kiếm tin theo keyword trong tất cả RSS feeds."""
        keyword = kwargs.get("keyword", symbol or "")
        limit   = kwargs.get("limit", 10)
        source  = kwargs.get("source", "all")

        if not keyword:
            return {"success": False, "error": "Cần cung cấp keyword hoặc symbol để tìm kiếm"}

        feeds = self._select_feeds(source, "home")
        articles = self._parse_feeds(feeds, limit_per_feed=50)
        filtered = self._filter_by_keyword(articles, keyword)
        filtered = filtered[:limit]

        return {
            "success": True,
            "report":  "search_news",
            "keyword": keyword,
            "source":  source,
            "count":   len(filtered),
            "data":    filtered,
        }



    def _fetch_html(self, url: str) -> Optional["BeautifulSoup"]:
        """Lấy HTML từ URL bài viết (chỉ dùng để đọc nội dung full article)."""
        html_headers = {
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        }
        try:
            resp = requests.get(url, headers=html_headers, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.warning(f"Lỗi fetch article {url}: {e}")
            return None

    async def get_article_content(self, url: str) -> Dict[str, Any]:
        """
        Lấy nội dung đầy đủ 1 bài viết từ URL.
        Dùng cho Sentiment Analysis.
        """
        if not url:
            return {"success": False, "error": "Cần cung cấp URL bài viết"}

        try:
            soup = self._fetch_html(url)
            if not soup:
                return {"success": False, "error": f"Không thể truy cập {url}"}

            # Title
            title = ""
            title_tag = soup.select_one("h1, .title-detail, .title-news")
            if title_tag:
                title = re.sub(r"\s+", " ", title_tag.get_text()).strip()

            # Content
            content = ""
            for selector in [
                ".fck_detail",       # VnExpress
                ".detail-content",   # CafeF
                ".content-detail",   # Vietstock
                "article .body",
                ".article-content",
                "#mainContent",
            ]:
                tag = soup.select_one(selector)
                if tag:
                    paragraphs = tag.find_all("p")
                    if paragraphs:
                        content = "\n".join(
                            re.sub(r"\s+", " ", p.get_text()).strip()
                            for p in paragraphs
                            if re.sub(r"\s+", " ", p.get_text()).strip()
                        )
                    else:
                        content = re.sub(r"\s+", " ", tag.get_text()).strip()
                    break

            if not content:
                all_p = soup.find_all("p")
                content = "\n".join(
                    re.sub(r"\s+", " ", p.get_text()).strip()
                    for p in all_p
                    if len(re.sub(r"\s+", " ", p.get_text()).strip()) > 30
                )

            return {
                "success":        True,
                "url":            url,
                "title":          title,
                "content":        content[:5000],
                "content_length": len(content),
            }

        except Exception as e:
            return {"success": False, "error": f"Lỗi lấy nội dung: {str(e)}"}



    def _select_feeds(self, source: str, category: str) -> List[tuple]:
        """Chọn feeds theo source filter và category."""
        feeds = RSS_FEEDS.get(category, RSS_FEEDS["home"])
        if source == "all":
            return feeds
        return [(name, url) for name, url in feeds if name.lower().startswith(source.lower())]
