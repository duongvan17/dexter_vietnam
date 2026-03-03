
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.news.aggregator import NewsAggregatorTool
from typing import Dict, Any, Optional, List
import re
import logging

logger = logging.getLogger(__name__)


POSITIVE_KEYWORDS = [
    # Xu hướng tăng
    "tăng mạnh", "tăng trần", "bứt phá", "tăng vọt", "phục hồi",
    "khởi sắc", "lạc quan", "tích cực", "đột phá", "tăng trưởng",
    "lợi nhuận tăng", "doanh thu tăng", "kỷ lục", "vượt kỳ vọng",
    "mua ròng", "dòng tiền vào", "hấp dẫn", "tiềm năng",
    "cơ hội", "triển vọng tốt", "khuyến nghị mua", "outperform",
    "nâng mục tiêu", "cổ tức cao", "lãi lớn", "hiệu quả",
    # Vĩ mô tích cực
    "GDP tăng", "xuất khẩu tăng", "FDI tăng", "giải ngân",
    "hạ lãi suất", "nới room", "tháo gỡ", "hỗ trợ",
]

NEGATIVE_KEYWORDS = [
    # Xu hướng giảm
    "giảm mạnh", "giảm sàn", "lao dốc", "bán tháo", "rớt giá",
    "bi quan", "tiêu cực", "sụt giảm", "bán ròng", "rút vốn",
    "thua lỗ", "lỗ nặng", "doanh thu giảm", "lợi nhuận giảm",
    "dưới kỳ vọng", "cảnh báo", "rủi ro", "nợ xấu", "vỡ nợ",
    "khuyến nghị bán", "underperform", "hạ mục tiêu",
    "phá sản", "thanh tra", "vi phạm", "xử phạt", "đình chỉ",
    # Vĩ mô tiêu cực
    "lạm phát tăng", "tăng lãi suất", "siết tín dụng",
    "suy thoái", "bất ổn", "biến động", "căng thẳng",
]


class SentimentAnalysisTool(BaseTool):

    def __init__(self, llm=None):

        self._llm = llm
        self._news_tool = NewsAggregatorTool()

    def get_name(self) -> str:
        return "sentiment_analysis"

    def get_description(self) -> str:
        return (
            "Phân tích tâm lý tin tức chứng khoán: positive/negative/neutral, "
            "điểm số 0-1, lý do."
        )

    def get_actions(self) -> dict:
        return {
            "analyze": "Phân tích sentiment cho 1 mã (tự động lấy tin + phân tích)",
            "stock_sentiment": "Tổng hợp sentiment nhiều tin của 1 mã cổ phiếu",
            "market_sentiment": "Sentiment tổng quan thị trường",
            "analyze_text": "Phân tích sentiment của 1 URL bài báo cụ thể",
        }

    def get_parameters_schema(self) -> dict:
        symbol_param = {
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Mã cổ phiếu (VD: FPT, VNM)",
                }
            },
            "required": ["symbol"],
        }
        return {
            "analyze": symbol_param,
            "stock_sentiment": symbol_param,
            "market_sentiment": {"properties": {}, "required": []},
            "analyze_text": {
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL bài báo cần phân tích sentiment",
                    }
                },
                "required": ["url"],
            },
        }


    def run(self, symbol: str = "", action: str = "analyze", **kwargs) -> Dict[str, Any]:
 
        action_map = {
            "analyze": self._analyze_article,
            "analyze_text": self._analyze_text,
            "stock_sentiment": self._stock_sentiment,
            "market_sentiment": self._market_sentiment,
        }
        if action not in action_map:
            return {"success": False, "error": f"Action không hợp lệ: {action}"}
        try:
            return action_map[action](symbol, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _analyze_article(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """
        Phân tích sentiment của bài viết.
        - Nếu có URL: phân tích bài viết đó
        - Nếu không có URL nhưng có symbol: tự động lấy tin và phân tích sentiment tổng hợp
        """
        url = kwargs.get("url", "")
        
        # Nếu không có URL nhưng có symbol → chuyển sang stock_sentiment
        if not url:
            if symbol:
                logger.info(f"No URL provided, auto-switching to stock_sentiment for {symbol}")
                return self._stock_sentiment(symbol, **kwargs)
            else:
                return {"success": False, "error": "Cần cung cấp URL bài viết hoặc mã cổ phiếu (symbol)"}

        # Lấy nội dung bài viết từ URL
        article = self._news_tool.get_article_content(url)
        if not article.get("success"):
            return article

        title = article.get("title", "")
        content = article.get("content", "")
        full_text = f"{title}\n{content}"

        # Phân tích sentiment
        result = self._do_sentiment(full_text, title=title)

        return {
            "success": True,
            "report": "article_sentiment",
            "url": url,
            "title": title,
            "sentiment": result,
        }


    def _analyze_text(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Phân tích sentiment từ text trực tiếp."""
        text = kwargs.get("text", "")
        title = kwargs.get("title", "")
        if not text:
            return {"success": False, "error": "Cần cung cấp text để phân tích"}

        full_text = f"{title}\n{text}" if title else text
        result = self._do_sentiment(full_text, title=title)

        return {
            "success": True,
            "report": "text_sentiment",
            "title": title,
            "text_length": len(text),
            "sentiment": result,
        }


    def _stock_sentiment(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Lấy tin RSS + phân tích sentiment tổng hợp cho 1 mã."""
        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        limit = kwargs.get("limit", 5)
        source = kwargs.get("source", "all")

        news_result = self._news_tool.run(
            symbol=symbol, action="stock_news", limit=limit, source=source
        )
        if not news_result.get("success"):
            return news_result

        articles = news_result.get("data", [])
        if not articles:
            return {
                "success": True,
                "symbol": symbol.upper(),
                "report": "stock_sentiment",
                "data": [],
                "overall": {"sentiment": "neutral", "score": 0.5, "reasoning": "Không tìm thấy tin tức"},
            }

        sentiments = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}"
            if text.strip():
                result = self._do_sentiment(text, title=article.get("title", ""))
                sentiments.append({
                    "title":     article.get("title", ""),
                    "url":       article.get("url", ""),
                    "source":    article.get("source", ""),
                    "published": article.get("published", ""),
                    "sentiment": result,
                })

        overall = self._compute_overall_sentiment(sentiments)

        return {
            "success":          True,
            "symbol":           symbol.upper(),
            "report":           "stock_sentiment",
            "articles_analyzed": len(sentiments),
            "data":             sentiments,
            "overall":          overall,
        }


    def _market_sentiment(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Phân tích tâm lý thị trường chung dựa trên RSS."""
        limit  = kwargs.get("limit", 10)
        source = kwargs.get("source", "all")

        news_result = self._news_tool.run(
            action="market", limit=limit, source=source
        )
        if not news_result.get("success"):
            return news_result

        articles = news_result.get("data", [])
        if not articles:
            return {
                "success": True,
                "report":  "market_sentiment",
                "data":    [],
                "overall": {"sentiment": "neutral", "score": 0.5, "reasoning": "Không có tin tức"},
            }

        sentiments = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}"
            if text.strip():
                result = self._do_sentiment(text, title=article.get("title", ""))
                sentiments.append({
                    "title":     article.get("title", ""),
                    "source":    article.get("source", ""),
                    "published": article.get("published", ""),
                    "sentiment": result,
                })

        overall = self._compute_overall_sentiment(sentiments)

        return {
            "success":           True,
            "report":            "market_sentiment",
            "articles_analyzed": len(sentiments),
            "data":              sentiments,
            "overall":           overall,
        }



    def _do_sentiment(self, text: str, title: str = "") -> Dict[str, Any]:

        # Thử LLM trước
        if self._llm is not None:
            try:
                return self._llm_sentiment(text, title)
            except Exception as e:
                logger.warning(f"LLM sentiment failed, fallback to keyword: {e}")

        # Keyword-based fallback
        return self._keyword_sentiment(text)

    def _llm_sentiment(self, text: str, title: str = "") -> Dict[str, Any]:
        """Phân tích sentiment bằng LLM."""
        system_prompt = """Bạn là chuyên gia phân tích tâm lý tin tức chứng khoán Việt Nam.
Phân tích bài viết sau và trả về JSON với format:
{
    "sentiment": "positive" hoặc "negative" hoặc "neutral",
    "score": số từ 0.0 đến 1.0 (0=rất tiêu cực, 0.5=trung tính, 1.0=rất tích cực),
    "reasoning": "Lý do ngắn gọn bằng tiếng Việt (1-2 câu)"
}

Chỉ trả về JSON, không thêm gì khác."""

        prompt = f"Tiêu đề: {title}\n\nNội dung:\n{text[:3000]}"

        result = self._llm.generate_json(prompt=prompt, system_prompt=system_prompt)

        if isinstance(result, dict) and "sentiment" in result:
            result["method"] = "llm"
            return result

        # Parse thất bại
        raise ValueError("LLM không trả về format đúng")

    def _keyword_sentiment(self, text: str) -> Dict[str, Any]:
 
        text_lower = text.lower()

        pos_count = 0
        neg_count = 0
        pos_found = []
        neg_found = []

        for kw in POSITIVE_KEYWORDS:
            count = text_lower.count(kw.lower())
            if count > 0:
                pos_count += count
                pos_found.append(kw)

        for kw in NEGATIVE_KEYWORDS:
            count = text_lower.count(kw.lower())
            if count > 0:
                neg_count += count
                neg_found.append(kw)

        total = pos_count + neg_count

        if total == 0:
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "reasoning": "Không tìm thấy từ khoá tâm lý rõ ràng",
                "method": "keyword",
                "keywords": {"positive": [], "negative": []},
            }

        # Tính score: pos_ratio → scale lên [0, 1]
        pos_ratio = pos_count / total
        score = round(pos_ratio, 2)

        if score >= 0.65:
            sentiment = "positive"
            emoji = "🟢"
        elif score <= 0.35:
            sentiment = "negative"
            emoji = "🔴"
        else:
            sentiment = "neutral"
            emoji = "🟡"

        # Tạo reasoning
        if pos_found and neg_found:
            reasoning = (
                f"{emoji} Tích cực ({pos_count}): {', '.join(pos_found[:3])}. "
                f"Tiêu cực ({neg_count}): {', '.join(neg_found[:3])}"
            )
        elif pos_found:
            reasoning = f"{emoji} Tín hiệu tích cực: {', '.join(pos_found[:4])}"
        elif neg_found:
            reasoning = f"{emoji} Tín hiệu tiêu cực: {', '.join(neg_found[:4])}"
        else:
            reasoning = f"{emoji} Trung tính"

        return {
            "sentiment": sentiment,
            "score": score,
            "reasoning": reasoning,
            "method": "keyword",
            "keywords": {
                "positive": pos_found[:5],
                "negative": neg_found[:5],
            },
        }


    def _compute_overall_sentiment(self, sentiments: List[Dict]) -> Dict[str, Any]:
        """Tổng hợp sentiment từ nhiều bài viết."""
        if not sentiments:
            return {"sentiment": "neutral", "score": 0.5, "reasoning": "Không có dữ liệu"}

        scores = []
        pos = 0
        neg = 0
        neu = 0

        for item in sentiments:
            s = item.get("sentiment", {})
            score_val = s.get("score", 0.5)
            scores.append(score_val)
            sent = s.get("sentiment", "neutral")
            if sent == "positive":
                pos += 1
            elif sent == "negative":
                neg += 1
            else:
                neu += 1

        avg_score = round(sum(scores) / len(scores), 2)
        total = len(sentiments)

        if avg_score >= 0.6:
            overall_sent = "positive"
            label = "🟢 TÍCH CỰC"
        elif avg_score <= 0.4:
            overall_sent = "negative"
            label = "🔴 TIÊU CỰC"
        else:
            overall_sent = "neutral"
            label = "🟡 TRUNG TÍNH"

        reasoning = (
            f"{label} - Điểm trung bình: {avg_score}/1.0 | "
            f"Tích cực: {pos}/{total}, Tiêu cực: {neg}/{total}, "
            f"Trung tính: {neu}/{total}"
        )

        return {
            "sentiment": overall_sent,
            "score": avg_score,
            "reasoning": reasoning,
            "breakdown": {
                "positive": pos,
                "negative": neg,
                "neutral": neu,
                "total": total,
            },
        }
