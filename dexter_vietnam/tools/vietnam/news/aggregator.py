"""
Module 5.1: News Aggregator
Thu thập tin tức chứng khoán từ nhiều nguồn Việt Nam

Theo CODING_ROADMAP.md - Module 5
Nguồn: CafeF, VnExpress, Vietstock, BaoDauTu
Tech: BeautifulSoup4 + requests
"""
from dexter_vietnam.tools.base import BaseTool
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re
import logging

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

logger = logging.getLogger(__name__)

# User-Agent để tránh bị block
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

# Cấu hình nguồn tin
NEWS_SOURCES = {
    "cafef": {
        "name": "CafeF",
        "base_url": "https://cafef.vn",
        "search_url": "https://cafef.vn/tim-kiem.chn",
        "stock_url": "https://cafef.vn/du-lieu/tin-tuc-doanh-nghiep/{symbol}.chn",
        "rss_url": "https://cafef.vn/rss/trang-chu.rss",
        "category_urls": {
            "market": "https://cafef.vn/thi-truong-chung-khoan.chn",
            "business": "https://cafef.vn/doanh-nghiep.chn",
            "macro": "https://cafef.vn/vi-mo-dau-tu.chn",
        },
    },
    "vnexpress": {
        "name": "VnExpress",
        "base_url": "https://vnexpress.net",
        "search_url": "https://timkiem.vnexpress.net",
        "rss_url": "https://vnexpress.net/rss/kinh-doanh.rss",
        "category_urls": {
            "market": "https://vnexpress.net/kinh-doanh/chung-khoan",
            "business": "https://vnexpress.net/kinh-doanh/doanh-nghiep",
            "macro": "https://vnexpress.net/kinh-doanh/vi-mo",
        },
    },
    "vietstock": {
        "name": "Vietstock",
        "base_url": "https://vietstock.vn",
        "search_url": "https://vietstock.vn/search",
        "category_urls": {
            "market": "https://vietstock.vn/chung-khoan.htm",
            "analysis": "https://vietstock.vn/phan-tich.htm",
        },
    },
}


class NewsAggregatorTool(BaseTool):
    """
    Thu thập tin tức chứng khoán từ nhiều nguồn:
    - CafeF, VnExpress, Vietstock
    - Tìm kiếm theo mã CP hoặc keyword
    - RSS feeds
    - Tin theo danh mục (thị trường, doanh nghiệp, vĩ mô)
    """

    REQUEST_TIMEOUT = 15  # seconds

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
            "Thu thập tin tức chứng khoán Việt Nam từ CafeF, VnExpress, Vietstock. "
            "Tìm kiếm theo mã cổ phiếu hoặc từ khoá."
        )

    async def run(self, symbol: str = "", action: str = "latest", **kwargs) -> Dict[str, Any]:
        """
        Args:
            symbol: Mã cổ phiếu (tuỳ chọn)
            action: Loại tin tức
                - latest: Tin mới nhất (mặc định)
                - search: Tìm kiếm theo keyword
                - stock_news: Tin theo mã CP
                - market: Tin thị trường chung
                - rss: Lấy tin từ RSS feeds
            **kwargs:
                keyword: Từ khoá tìm kiếm
                source: Nguồn tin (cafef, vnexpress, vietstock, all)
                limit: Số tin trả về (mặc định 10)
        """
        action_map = {
            "latest": self._get_latest_news,
            "search": self._search_news,
            "stock_news": self._get_stock_news,
            "market": self._get_market_news,
            "rss": self._get_rss_news,
        }
        if action not in action_map:
            return {"success": False, "error": f"Action không hợp lệ: {action}"}
        try:
            return await action_map[action](symbol, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===================================================================
    # Helpers
    # ===================================================================

    def _fetch_html(self, url: str) -> Optional[BeautifulSoup]:
        """Lấy HTML từ URL và parse bằng BeautifulSoup."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.warning(f"Lỗi fetch {url}: {e}")
            return None

    def _fetch_rss(self, url: str) -> Optional[BeautifulSoup]:
        """Lấy RSS feed và parse XML."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return BeautifulSoup(resp.text, "lxml-xml")
        except Exception as e:
            logger.warning(f"Lỗi fetch RSS {url}: {e}")
            return None

    def _clean_text(self, text: Optional[str]) -> str:
        """Làm sạch text: bỏ ký tự thừa, khoảng trắng."""
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_date(self, text: Optional[str]) -> Optional[str]:
        """Trích xuất ngày từ chuỗi text."""
        if not text:
            return None
        # Thử các format phổ biến
        patterns = [
            r"(\d{2}/\d{2}/\d{4})",
            r"(\d{4}-\d{2}-\d{2})",
            r"(\d{2}-\d{2}-\d{4})",
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                return match.group(1)
        return text.strip()[:20] if text else None

    # ===================================================================
    # 1. LATEST NEWS (Tin mới nhất)
    # ===================================================================

    async def _get_latest_news(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Lấy tin mới nhất từ tất cả nguồn."""
        limit = kwargs.get("limit", 10)
        source = kwargs.get("source", "all")

        all_news = []

        if source in ("all", "cafef"):
            all_news.extend(self._crawl_cafef_latest(limit))

        if source in ("all", "vnexpress"):
            all_news.extend(self._crawl_vnexpress_latest(limit))

        if source in ("all", "vietstock"):
            all_news.extend(self._crawl_vietstock_latest(limit))

        # Nếu có symbol, lọc tin liên quan
        if symbol:
            symbol_upper = symbol.upper()
            filtered = [
                n for n in all_news
                if symbol_upper in (n.get("title", "") + n.get("summary", "")).upper()
            ]
            if filtered:
                all_news = filtered

        # Giới hạn số lượng
        all_news = all_news[:limit]

        return {
            "success": True,
            "report": "latest_news",
            "source": source,
            "count": len(all_news),
            "data": all_news,
        }

    def _crawl_cafef_latest(self, limit: int = 10) -> List[Dict]:
        """Crawl tin mới nhất từ CafeF."""
        news = []
        url = NEWS_SOURCES["cafef"]["category_urls"]["market"]
        soup = self._fetch_html(url)
        if not soup:
            return news

        # CafeF: tìm các article items
        articles = soup.select("h3 a, h2 a, .title a, .knswli-title a")
        seen_urls = set()

        for tag in articles[:limit * 2]:
            title = self._clean_text(tag.get_text())
            href = tag.get("href", "")

            if not title or len(title) < 10:
                continue

            # Xây dựng URL đầy đủ
            if href and not href.startswith("http"):
                href = NEWS_SOURCES["cafef"]["base_url"] + href

            if href in seen_urls:
                continue
            seen_urls.add(href)

            news.append({
                "title": title,
                "url": href,
                "source": "CafeF",
                "summary": "",
            })

            if len(news) >= limit:
                break

        return news

    def _crawl_vnexpress_latest(self, limit: int = 10) -> List[Dict]:
        """Crawl tin mới nhất từ VnExpress Kinh doanh / Chứng khoán."""
        news = []
        url = NEWS_SOURCES["vnexpress"]["category_urls"]["market"]
        soup = self._fetch_html(url)
        if not soup:
            return news

        articles = soup.select("h3.title-news a, h2.title-news a, .title-news a")
        seen_urls = set()

        for tag in articles[:limit * 2]:
            title = self._clean_text(tag.get_text())
            href = tag.get("href", "")

            if not title or len(title) < 10:
                continue

            if href in seen_urls:
                continue
            seen_urls.add(href)

            # Tìm description
            parent = tag.find_parent("article") or tag.find_parent("div")
            summary = ""
            if parent:
                desc_tag = parent.select_one("p.description, .description")
                if desc_tag:
                    summary = self._clean_text(desc_tag.get_text())

            news.append({
                "title": title,
                "url": href,
                "source": "VnExpress",
                "summary": summary,
            })

            if len(news) >= limit:
                break

        return news

    def _crawl_vietstock_latest(self, limit: int = 10) -> List[Dict]:
        """Crawl tin mới nhất từ Vietstock."""
        news = []
        url = NEWS_SOURCES["vietstock"]["category_urls"]["market"]
        soup = self._fetch_html(url)
        if not soup:
            return news

        articles = soup.select("h4 a, h3 a, .title a, .content-title a")
        seen_urls = set()

        for tag in articles[:limit * 2]:
            title = self._clean_text(tag.get_text())
            href = tag.get("href", "")

            if not title or len(title) < 10:
                continue

            if href and not href.startswith("http"):
                href = NEWS_SOURCES["vietstock"]["base_url"] + href

            if href in seen_urls:
                continue
            seen_urls.add(href)

            news.append({
                "title": title,
                "url": href,
                "source": "Vietstock",
                "summary": "",
            })

            if len(news) >= limit:
                break

        return news

    # ===================================================================
    # 2. SEARCH NEWS (Tìm kiếm)
    # ===================================================================

    async def _search_news(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Tìm kiếm tin tức theo keyword."""
        keyword = kwargs.get("keyword", symbol or "")
        limit = kwargs.get("limit", 10)
        source = kwargs.get("source", "all")

        if not keyword:
            return {"success": False, "error": "Cần cung cấp keyword hoặc symbol để tìm kiếm"}

        all_news = []

        if source in ("all", "cafef"):
            all_news.extend(self._search_cafef(keyword, limit))

        if source in ("all", "vnexpress"):
            all_news.extend(self._search_vnexpress(keyword, limit))

        all_news = all_news[:limit]

        return {
            "success": True,
            "report": "search_news",
            "keyword": keyword,
            "source": source,
            "count": len(all_news),
            "data": all_news,
        }

    def _search_cafef(self, keyword: str, limit: int = 10) -> List[Dict]:
        """Tìm kiếm tin trên CafeF."""
        news = []
        try:
            url = f"https://cafef.vn/tim-kiem.chn?keywords={requests.utils.quote(keyword)}"
            soup = self._fetch_html(url)
            if not soup:
                return news

            articles = soup.select(".list-news li, .search-result-item, h3 a")
            seen_urls = set()

            for item in articles[:limit * 2]:
                # Tìm link
                link_tag = item if item.name == "a" else item.select_one("a")
                if not link_tag:
                    continue

                title = self._clean_text(link_tag.get_text())
                href = link_tag.get("href", "")

                if not title or len(title) < 10:
                    continue

                if href and not href.startswith("http"):
                    href = "https://cafef.vn" + href

                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # Summary
                summary = ""
                desc = item.select_one("p, .sapo, .summary")
                if desc:
                    summary = self._clean_text(desc.get_text())

                news.append({
                    "title": title,
                    "url": href,
                    "source": "CafeF",
                    "summary": summary,
                })

                if len(news) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Lỗi search CafeF: {e}")

        return news

    def _search_vnexpress(self, keyword: str, limit: int = 10) -> List[Dict]:
        """Tìm kiếm tin trên VnExpress."""
        news = []
        try:
            url = f"https://timkiem.vnexpress.net/?q={requests.utils.quote(keyword)}"
            soup = self._fetch_html(url)
            if not soup:
                return news

            articles = soup.select("article.item-news, .item-news-common, h3.title-news a")
            seen_urls = set()

            for item in articles[:limit * 2]:
                link_tag = item if item.name == "a" else item.select_one("h3 a, .title-news a, a")
                if not link_tag:
                    continue

                title = self._clean_text(link_tag.get_text())
                href = link_tag.get("href", "")

                if not title or len(title) < 10:
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                summary = ""
                desc = item.select_one("p.description, .description")
                if desc:
                    summary = self._clean_text(desc.get_text())

                news.append({
                    "title": title,
                    "url": href,
                    "source": "VnExpress",
                    "summary": summary,
                })

                if len(news) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Lỗi search VnExpress: {e}")

        return news

    # ===================================================================
    # 3. STOCK NEWS (Tin theo mã CP)
    # ===================================================================

    async def _get_stock_news(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Lấy tin tức liên quan đến 1 mã cổ phiếu."""
        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        limit = kwargs.get("limit", 10)
        all_news = []

        # Tìm tin trực tiếp theo mã CP trên CafeF
        all_news.extend(self._crawl_cafef_stock(symbol, limit))

        # Bổ sung bằng search
        all_news.extend(self._search_cafef(symbol, limit))
        all_news.extend(self._search_vnexpress(symbol, limit))

        # Deduplicate theo title
        seen = set()
        unique = []
        for n in all_news:
            title_key = n.get("title", "").strip().lower()[:50]
            if title_key not in seen:
                seen.add(title_key)
                unique.append(n)

        unique = unique[:limit]

        return {
            "success": True,
            "report": "stock_news",
            "symbol": symbol.upper(),
            "count": len(unique),
            "data": unique,
        }

    def _crawl_cafef_stock(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Crawl tin theo mã CP trên CafeF."""
        news = []
        # CafeF có trang tin theo mã CP
        url = f"https://cafef.vn/du-lieu/tin-tuc-doanh-nghiep/{symbol.upper()}.chn"
        soup = self._fetch_html(url)
        if not soup:
            return news

        articles = soup.select("h3 a, .title a, .knswli-title a")
        seen_urls = set()

        for tag in articles[:limit * 2]:
            title = self._clean_text(tag.get_text())
            href = tag.get("href", "")

            if not title or len(title) < 10:
                continue

            if href and not href.startswith("http"):
                href = "https://cafef.vn" + href

            if href in seen_urls:
                continue
            seen_urls.add(href)

            news.append({
                "title": title,
                "url": href,
                "source": "CafeF",
                "symbol": symbol.upper(),
                "summary": "",
            })

            if len(news) >= limit:
                break

        return news

    # ===================================================================
    # 4. MARKET NEWS (Tin thị trường)
    # ===================================================================

    async def _get_market_news(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Lấy tin thị trường chung (vĩ mô, nhận định, phân tích)."""
        limit = kwargs.get("limit", 15)
        category = kwargs.get("category", "market")  # market, business, macro
        source = kwargs.get("source", "all")

        all_news = []

        if source in ("all", "cafef"):
            cat_url = NEWS_SOURCES["cafef"]["category_urls"].get(category)
            if cat_url:
                soup = self._fetch_html(cat_url)
                if soup:
                    articles = soup.select("h3 a, h2 a, .title a")
                    for tag in articles[:limit]:
                        title = self._clean_text(tag.get_text())
                        href = tag.get("href", "")
                        if title and len(title) >= 10:
                            if href and not href.startswith("http"):
                                href = "https://cafef.vn" + href
                            all_news.append({
                                "title": title, "url": href,
                                "source": "CafeF", "category": category,
                            })

        if source in ("all", "vnexpress"):
            cat_url = NEWS_SOURCES["vnexpress"]["category_urls"].get(category)
            if cat_url:
                soup = self._fetch_html(cat_url)
                if soup:
                    articles = soup.select("h3.title-news a, h2.title-news a")
                    for tag in articles[:limit]:
                        title = self._clean_text(tag.get_text())
                        href = tag.get("href", "")
                        if title and len(title) >= 10:
                            all_news.append({
                                "title": title, "url": href,
                                "source": "VnExpress", "category": category,
                            })

        # Deduplicate
        seen = set()
        unique = []
        for n in all_news:
            key = n["title"].strip().lower()[:50]
            if key not in seen:
                seen.add(key)
                unique.append(n)

        unique = unique[:limit]

        return {
            "success": True,
            "report": "market_news",
            "category": category,
            "count": len(unique),
            "data": unique,
        }

    # ===================================================================
    # 5. RSS NEWS
    # ===================================================================

    async def _get_rss_news(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Lấy tin từ RSS feeds (nhanh, ổn định hơn crawl HTML)."""
        limit = kwargs.get("limit", 15)
        source = kwargs.get("source", "all")

        all_news = []

        rss_feeds = []
        if source in ("all", "cafef"):
            rss_feeds.append(("CafeF", NEWS_SOURCES["cafef"]["rss_url"]))
        if source in ("all", "vnexpress"):
            rss_feeds.append(("VnExpress", NEWS_SOURCES["vnexpress"]["rss_url"]))

        for src_name, rss_url in rss_feeds:
            soup = self._fetch_rss(rss_url)
            if not soup:
                continue

            items = soup.find_all("item")
            for item in items[:limit]:
                title = self._clean_text(item.find("title").get_text() if item.find("title") else "")
                link = item.find("link")
                url = self._clean_text(link.get_text() if link else "")
                # Một số RSS có link text dưới dạng CDATA hoặc next sibling
                if not url and link:
                    url = link.string or ""
                    if not url:
                        # link có thể nằm sau tag
                        url = str(link.next_sibling).strip() if link.next_sibling else ""

                pub_date = ""
                date_tag = item.find("pubDate") or item.find("pubdate")
                if date_tag:
                    pub_date = self._clean_text(date_tag.get_text())

                description = ""
                desc_tag = item.find("description")
                if desc_tag:
                    # RSS description thường chứa HTML
                    desc_soup = BeautifulSoup(desc_tag.get_text(), "lxml")
                    description = self._clean_text(desc_soup.get_text())[:200]

                if title and len(title) >= 10:
                    entry = {
                        "title": title,
                        "url": url.strip(),
                        "source": src_name,
                        "published": pub_date,
                        "summary": description,
                    }
                    all_news.append(entry)

        # Lọc theo symbol nếu có
        if symbol:
            sym_upper = symbol.upper()
            filtered = [
                n for n in all_news
                if sym_upper in (n.get("title", "") + n.get("summary", "")).upper()
            ]
            if filtered:
                all_news = filtered

        all_news = all_news[:limit]

        return {
            "success": True,
            "report": "rss_news",
            "source": source,
            "count": len(all_news),
            "data": all_news,
        }

    # ===================================================================
    # Public helper: lấy nội dung bài viết
    # ===================================================================

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

            # Tìm nội dung chính
            content = ""
            title = ""

            # Title
            title_tag = soup.select_one("h1, .title-detail, .title-news")
            if title_tag:
                title = self._clean_text(title_tag.get_text())

            # Content - thử nhiều selector phổ biến
            content_selectors = [
                ".fck_detail",           # VnExpress
                ".detail-content",       # CafeF
                ".content-detail",       # Vietstock
                "article .body",
                ".article-content",
                "#mainContent",
                ".post-content",
            ]

            for selector in content_selectors:
                content_tag = soup.select_one(selector)
                if content_tag:
                    # Lấy text từ các thẻ p
                    paragraphs = content_tag.find_all("p")
                    if paragraphs:
                        content = "\n".join(
                            self._clean_text(p.get_text()) for p in paragraphs
                            if self._clean_text(p.get_text())
                        )
                    else:
                        content = self._clean_text(content_tag.get_text())
                    break

            if not content:
                # Fallback: lấy tất cả thẻ <p>
                all_p = soup.find_all("p")
                content = "\n".join(
                    self._clean_text(p.get_text()) for p in all_p
                    if len(self._clean_text(p.get_text())) > 30
                )

            return {
                "success": True,
                "url": url,
                "title": title,
                "content": content[:5000],  # Giới hạn 5000 ký tự
                "content_length": len(content),
            }

        except Exception as e:
            return {"success": False, "error": f"Lỗi lấy nội dung: {str(e)}"}
