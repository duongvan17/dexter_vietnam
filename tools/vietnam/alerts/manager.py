"""
Module 11: Alerts - Hệ thống cảnh báo giá & tin tức

Theo CODING_ROADMAP.md - Module 11:
- create_price_alert: Tạo cảnh báo giá
- create_news_alert: Tạo cảnh báo tin tức
- check_alerts: Kiểm tra & kích hoạt alerts
- list_alerts: Liệt kê tất cả alerts
- delete_alert: Xóa alert
- alert_history: Lịch sử alerts đã kích hoạt

Storage: JSON file (alerts.json)
"""
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import os
import uuid
import logging

logger = logging.getLogger(__name__)

# Default alerts storage path
DEFAULT_ALERTS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "data", "alerts.json"
)


class AlertManager:
    """Quản lý lưu trữ alerts với JSON file."""

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or DEFAULT_ALERTS_FILE
        self._ensure_file()

    def _ensure_file(self):
        """Tạo file & thư mục nếu chưa có."""
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.filepath):
            self._save({"alerts": [], "history": []})

    def _load(self) -> Dict:
        """Load data from JSON file."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"alerts": [], "history": []}

    def _save(self, data: Dict):
        """Save data to JSON file."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def add_alert(self, alert: Dict) -> str:
        """Add a new alert. Returns alert_id."""
        data = self._load()
        alert_id = str(uuid.uuid4())[:8]
        alert["id"] = alert_id
        alert["created_at"] = datetime.now().isoformat()
        alert["active"] = True
        alert["triggered_count"] = 0
        data["alerts"].append(alert)
        self._save(data)
        return alert_id

    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts."""
        data = self._load()
        return [a for a in data["alerts"] if a.get("active", False)]

    def get_all_alerts(self) -> List[Dict]:
        """Get all alerts (active + inactive)."""
        data = self._load()
        return data["alerts"]

    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert by ID."""
        data = self._load()
        original_count = len(data["alerts"])
        data["alerts"] = [a for a in data["alerts"] if a["id"] != alert_id]
        if len(data["alerts"]) < original_count:
            self._save(data)
            return True
        return False

    def deactivate_alert(self, alert_id: str) -> bool:
        """Deactivate (but not delete) an alert."""
        data = self._load()
        for alert in data["alerts"]:
            if alert["id"] == alert_id:
                alert["active"] = False
                self._save(data)
                return True
        return False

    def record_trigger(self, alert_id: str, trigger_data: Dict):
        """Record an alert trigger in history."""
        data = self._load()
        # Update triggered_count
        for alert in data["alerts"]:
            if alert["id"] == alert_id:
                alert["triggered_count"] = alert.get("triggered_count", 0) + 1
                alert["last_triggered"] = datetime.now().isoformat()
                break
        # Add to history
        data["history"].append({
            "alert_id": alert_id,
            "triggered_at": datetime.now().isoformat(),
            **trigger_data,
        })
        # Keep history manageable (last 500 entries)
        if len(data["history"]) > 500:
            data["history"] = data["history"][-500:]
        self._save(data)

    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get trigger history."""
        data = self._load()
        return data["history"][-limit:]

    def clear_all(self):
        """Clear all alerts and history."""
        self._save({"alerts": [], "history": []})


class AlertsTool(BaseTool):
    """
    Hệ thống cảnh báo chứng khoán Việt Nam:
    - Cảnh báo giá (vượt ngưỡng, giảm dưới, % thay đổi)
    - Cảnh báo tin tức (keyword matching)
    - Cảnh báo kỹ thuật (RSI, MACD signals)
    - Kiểm tra & kích hoạt alerts tự động
    """

    def __init__(self, alerts_file: Optional[str] = None):
        self._data_tool = VnstockTool()
        self._manager = AlertManager(alerts_file)

    def get_name(self) -> str:
        return "alerts"

    def get_description(self) -> str:
        return (
            "Hệ thống cảnh báo chứng khoán: tạo cảnh báo giá "
            "(vượt ngưỡng, giảm dưới), cảnh báo chỉ báo kỹ thuật "
            "(RSI, volume), cảnh báo tin tức. Kiểm tra & kích hoạt alerts. "
            "Hỗ trợ: create_price, create_technical, create_news, "
            "check, list, delete, history, clear."
        )

    async def run(self, action: str = "list", **kwargs) -> Dict[str, Any]:
        """
        Thực thi action.

        Actions:
            create_price   - Tạo cảnh báo giá
            create_technical - Tạo cảnh báo kỹ thuật
            create_news    - Tạo cảnh báo tin tức
            check          - Kiểm tra tất cả alerts
            list           - Liệt kê alerts
            delete         - Xóa alert theo ID
            history        - Lịch sử kích hoạt
            clear          - Xóa tất cả alerts
        """
        action_map = {
            "create_price": self.create_price_alert,
            "create_technical": self.create_technical_alert,
            "create_news": self.create_news_alert,
            "check": self.check_alerts,
            "list": self.list_alerts,
            "delete": self.delete_alert,
            "history": self.get_alert_history,
            "clear": self.clear_alerts,
        }

        if action not in action_map:
            return {
                "success": False,
                "error": f"Action không hợp lệ: {action}. "
                         f"Sử dụng: {list(action_map.keys())}",
            }

        try:
            return await action_map[action](**kwargs)
        except Exception as e:
            logger.error(f"Alert action '{action}' failed: {e}", exc_info=True)
            return {"success": False, "error": f"Lỗi thực thi {action}: {str(e)}"}

    # =================================================================
    # CREATE PRICE ALERT
    # =================================================================

    async def create_price_alert(
        self,
        symbol: str,
        target_price: float,
        condition: str = "above",
        note: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Tạo cảnh báo giá.

        Args:
            symbol: Mã cổ phiếu (VD: VNM, FPT)
            target_price: Giá mục tiêu (nghìn VND)
            condition: Điều kiện kích hoạt
                - "above": Giá >= target_price
                - "below": Giá <= target_price
                - "change_up": Thay đổi % tăng >= target_price (%)
                - "change_down": Thay đổi % giảm >= target_price (%)
            note: Ghi chú tùy chọn
        """
        symbol = symbol.upper()
        if condition not in ("above", "below", "change_up", "change_down"):
            return {
                "success": False,
                "error": "condition phải là: above, below, change_up, change_down",
            }

        # Get current price for reference
        current_price = await self._get_current_price(symbol)

        alert = {
            "type": "price",
            "symbol": symbol,
            "target_price": target_price,
            "condition": condition,
            "note": note,
            "reference_price": current_price,
        }

        alert_id = self._manager.add_alert(alert)

        condition_text = {
            "above": f"≥ {target_price:,.1f}",
            "below": f"≤ {target_price:,.1f}",
            "change_up": f"tăng ≥ {target_price}%",
            "change_down": f"giảm ≥ {target_price}%",
        }

        return {
            "success": True,
            "alert_id": alert_id,
            "message": f"Đã tạo cảnh báo giá {symbol}: {condition_text[condition]}",
            "details": {
                "symbol": symbol,
                "condition": condition,
                "target": target_price,
                "current_price": current_price,
            },
        }

    # =================================================================
    # CREATE TECHNICAL ALERT
    # =================================================================

    async def create_technical_alert(
        self,
        symbol: str,
        indicator: str = "rsi",
        threshold: float = 30.0,
        condition: str = "below",
        note: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Tạo cảnh báo chỉ báo kỹ thuật.

        Args:
            symbol: Mã cổ phiếu
            indicator: Chỉ báo (rsi, volume_spike)
                - rsi: RSI vượt/giảm dưới ngưỡng
                - volume_spike: Khối lượng đột biến (x lần so trung bình)
            threshold: Ngưỡng kích hoạt
            condition: above hoặc below
            note: Ghi chú
        """
        symbol = symbol.upper()
        if indicator not in ("rsi", "volume_spike"):
            return {
                "success": False,
                "error": "indicator phải là: rsi, volume_spike",
            }
        if condition not in ("above", "below"):
            return {
                "success": False,
                "error": "condition phải là: above, below",
            }

        alert = {
            "type": "technical",
            "symbol": symbol,
            "indicator": indicator,
            "threshold": threshold,
            "condition": condition,
            "note": note,
        }

        alert_id = self._manager.add_alert(alert)

        desc_map = {
            "rsi": f"RSI {'≥' if condition == 'above' else '≤'} {threshold}",
            "volume_spike": f"Khối lượng {'≥' if condition == 'above' else '≤'} {threshold}x trung bình",
        }

        return {
            "success": True,
            "alert_id": alert_id,
            "message": f"Đã tạo cảnh báo kỹ thuật {symbol}: {desc_map[indicator]}",
            "details": {
                "symbol": symbol,
                "indicator": indicator,
                "threshold": threshold,
                "condition": condition,
            },
        }

    # =================================================================
    # CREATE NEWS ALERT
    # =================================================================

    async def create_news_alert(
        self,
        symbol: str = "",
        keywords: Optional[List[str]] = None,
        note: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Tạo cảnh báo tin tức.

        Args:
            symbol: Mã cổ phiếu (tùy chọn)
            keywords: Danh sách từ khóa cần theo dõi
            note: Ghi chú
        """
        if not symbol and not keywords:
            return {
                "success": False,
                "error": "Cần ít nhất symbol hoặc keywords",
            }

        if keywords is None:
            keywords = []

        # Auto-add symbol as keyword if provided
        if symbol and symbol.upper() not in [k.upper() for k in keywords]:
            keywords.insert(0, symbol.upper())

        alert = {
            "type": "news",
            "symbol": symbol.upper() if symbol else "",
            "keywords": keywords,
            "note": note,
        }

        alert_id = self._manager.add_alert(alert)
        kw_str = ", ".join(keywords)

        return {
            "success": True,
            "alert_id": alert_id,
            "message": f"Đã tạo cảnh báo tin tức: [{kw_str}]",
            "details": {
                "symbol": symbol.upper() if symbol else "",
                "keywords": keywords,
            },
        }

    # =================================================================
    # CHECK ALERTS
    # =================================================================

    async def check_alerts(self, **kwargs) -> Dict[str, Any]:
        """
        Kiểm tra tất cả alerts active → trả về danh sách alerts đã được kích hoạt.
        Lấy dữ liệu giá realtime, kiểm tra điều kiện, ghi lại triggers.
        """
        active_alerts = self._manager.get_active_alerts()
        if not active_alerts:
            return {
                "success": True,
                "triggered": [],
                "checked": 0,
                "message": "Không có alert nào đang active.",
            }

        triggered = []
        errors = []
        checked = 0

        # Group alerts by symbol to reduce API calls
        symbol_alerts: Dict[str, List[Dict]] = {}
        news_alerts: List[Dict] = []

        for alert in active_alerts:
            if alert["type"] == "news":
                news_alerts.append(alert)
            else:
                sym = alert.get("symbol", "")
                if sym:
                    symbol_alerts.setdefault(sym, []).append(alert)

        # Check price & technical alerts per symbol
        for symbol, alerts_list in symbol_alerts.items():
            try:
                # Get current price
                current_price = await self._get_current_price(symbol)
                if current_price is None:
                    errors.append(f"Không lấy được giá {symbol}")
                    continue

                # Get RSI if needed
                rsi_value = None
                volume_ratio = None
                need_rsi = any(
                    a.get("type") == "technical" and a.get("indicator") == "rsi"
                    for a in alerts_list
                )
                need_volume = any(
                    a.get("type") == "technical" and a.get("indicator") == "volume_spike"
                    for a in alerts_list
                )

                if need_rsi:
                    rsi_value = await self._get_rsi(symbol)
                if need_volume:
                    volume_ratio = await self._get_volume_ratio(symbol)

                for alert in alerts_list:
                    checked += 1
                    trigger_result = self._evaluate_alert(
                        alert, current_price, rsi_value, volume_ratio
                    )
                    if trigger_result["triggered"]:
                        triggered.append(trigger_result)
                        self._manager.record_trigger(alert["id"], trigger_result)

            except Exception as e:
                errors.append(f"Lỗi kiểm tra {symbol}: {str(e)}")

        # Check news alerts
        for alert in news_alerts:
            checked += 1
            try:
                trigger_result = await self._check_news_alert(alert)
                if trigger_result["triggered"]:
                    triggered.append(trigger_result)
                    self._manager.record_trigger(alert["id"], trigger_result)
            except Exception as e:
                errors.append(f"Lỗi kiểm tra tin tức: {str(e)}")

        return {
            "success": True,
            "checked": checked,
            "triggered_count": len(triggered),
            "triggered": triggered,
            "errors": errors if errors else None,
            "message": (
                f"Đã kiểm tra {checked} alerts. "
                f"{len(triggered)} alert được kích hoạt."
            ),
        }

    def _evaluate_alert(
        self,
        alert: Dict,
        current_price: Optional[float],
        rsi_value: Optional[float],
        volume_ratio: Optional[float],
    ) -> Dict[str, Any]:
        """Evaluate a single alert against current data."""
        alert_type = alert.get("type")
        result = {
            "alert_id": alert["id"],
            "symbol": alert.get("symbol", ""),
            "type": alert_type,
            "triggered": False,
        }

        if alert_type == "price" and current_price is not None:
            target = alert.get("target_price", 0)
            condition = alert.get("condition", "above")
            ref_price = alert.get("reference_price")

            if condition == "above" and current_price >= target:
                result["triggered"] = True
                result["message"] = (
                    f"🔔 {alert['symbol']}: Giá {current_price:,.1f} ≥ {target:,.1f}"
                )
            elif condition == "below" and current_price <= target:
                result["triggered"] = True
                result["message"] = (
                    f"🔔 {alert['symbol']}: Giá {current_price:,.1f} ≤ {target:,.1f}"
                )
            elif condition == "change_up" and ref_price and ref_price > 0:
                pct = ((current_price - ref_price) / ref_price) * 100
                if pct >= target:
                    result["triggered"] = True
                    result["message"] = (
                        f"🔔 {alert['symbol']}: Tăng {pct:+.1f}% (mục tiêu +{target}%)"
                    )
            elif condition == "change_down" and ref_price and ref_price > 0:
                pct = ((ref_price - current_price) / ref_price) * 100
                if pct >= target:
                    result["triggered"] = True
                    result["message"] = (
                        f"🔔 {alert['symbol']}: Giảm {pct:.1f}% (mục tiêu -{target}%)"
                    )

            result["current_price"] = current_price

        elif alert_type == "technical":
            indicator = alert.get("indicator")
            threshold = alert.get("threshold", 0)
            condition = alert.get("condition", "below")

            if indicator == "rsi" and rsi_value is not None:
                if condition == "below" and rsi_value <= threshold:
                    result["triggered"] = True
                    result["message"] = (
                        f"🔔 {alert['symbol']}: RSI = {rsi_value:.1f} ≤ {threshold}"
                    )
                elif condition == "above" and rsi_value >= threshold:
                    result["triggered"] = True
                    result["message"] = (
                        f"🔔 {alert['symbol']}: RSI = {rsi_value:.1f} ≥ {threshold}"
                    )
                result["rsi"] = rsi_value

            elif indicator == "volume_spike" and volume_ratio is not None:
                if condition == "above" and volume_ratio >= threshold:
                    result["triggered"] = True
                    result["message"] = (
                        f"🔔 {alert['symbol']}: Volume = {volume_ratio:.1f}x "
                        f"trung bình (ngưỡng {threshold}x)"
                    )
                elif condition == "below" and volume_ratio <= threshold:
                    result["triggered"] = True
                    result["message"] = (
                        f"🔔 {alert['symbol']}: Volume = {volume_ratio:.1f}x "
                        f"trung bình (ngưỡng ≤{threshold}x)"
                    )
                result["volume_ratio"] = volume_ratio

        return result

    async def _check_news_alert(self, alert: Dict) -> Dict[str, Any]:
        """Check news alert by searching for keywords."""
        keywords = alert.get("keywords", [])
        symbol = alert.get("symbol", "")
        result = {
            "alert_id": alert["id"],
            "symbol": symbol,
            "type": "news",
            "triggered": False,
        }

        try:
            from dexter_vietnam.tools.vietnam.news.aggregator import NewsAggregatorTool
            news_tool = NewsAggregatorTool()

            if symbol:
                news_data = await news_tool.run(
                    action="stock_news", symbol=symbol, limit=5
                )
            elif keywords:
                news_data = await news_tool.run(
                    action="search", keyword=keywords[0], limit=5
                )
            else:
                return result

            articles = news_data.get("data", news_data.get("articles", []))
            if not articles:
                return result

            # Check if any article matches keywords
            matched_articles = []
            for article in articles:
                title = (article.get("title", "") or "").lower()
                summary = (article.get("summary", "") or "").lower()
                text = f"{title} {summary}"

                for kw in keywords:
                    if kw.lower() in text:
                        matched_articles.append({
                            "title": article.get("title", ""),
                            "url": article.get("url", ""),
                            "matched_keyword": kw,
                        })
                        break

            if matched_articles:
                result["triggered"] = True
                result["matched_articles"] = matched_articles[:3]
                result["message"] = (
                    f"📰 Tin mới về [{', '.join(keywords)}]: "
                    f"{matched_articles[0]['title']}"
                )

        except Exception as e:
            logger.warning(f"News alert check failed: {e}")

        return result

    # =================================================================
    # LIST / DELETE / HISTORY / CLEAR
    # =================================================================

    async def list_alerts(self, **kwargs) -> Dict[str, Any]:
        """Liệt kê tất cả alerts."""
        active = self._manager.get_active_alerts()
        all_alerts = self._manager.get_all_alerts()
        inactive = [a for a in all_alerts if not a.get("active", False)]

        # Format for display
        formatted_active = []
        for a in active:
            item = {
                "id": a["id"],
                "type": a["type"],
                "symbol": a.get("symbol", ""),
                "created_at": a.get("created_at", ""),
                "triggered_count": a.get("triggered_count", 0),
            }
            if a["type"] == "price":
                cond = a.get("condition", "above")
                target = a.get("target_price", 0)
                item["description"] = f"Giá {cond} {target:,.1f}"
            elif a["type"] == "technical":
                ind = a.get("indicator", "")
                thresh = a.get("threshold", 0)
                cond = a.get("condition", "")
                item["description"] = f"{ind} {cond} {thresh}"
            elif a["type"] == "news":
                kws = a.get("keywords", [])
                item["description"] = f"Tin tức: {', '.join(kws)}"
            formatted_active.append(item)

        return {
            "success": True,
            "active_count": len(active),
            "inactive_count": len(inactive),
            "active_alerts": formatted_active,
            "message": f"{len(active)} alert đang active, {len(inactive)} đã tắt.",
        }

    async def delete_alert(
        self, alert_id: str = "", **kwargs
    ) -> Dict[str, Any]:
        """Xóa alert theo ID."""
        if not alert_id:
            return {"success": False, "error": "Cần cung cấp alert_id"}

        deleted = self._manager.delete_alert(alert_id)
        if deleted:
            return {
                "success": True,
                "message": f"Đã xóa alert {alert_id}.",
            }
        return {
            "success": False,
            "error": f"Không tìm thấy alert {alert_id}.",
        }

    async def get_alert_history(
        self, limit: int = 20, **kwargs
    ) -> Dict[str, Any]:
        """Lấy lịch sử kích hoạt alerts."""
        history = self._manager.get_history(limit=limit)
        return {
            "success": True,
            "count": len(history),
            "history": history,
            "message": f"Lịch sử {len(history)} lần kích hoạt gần nhất.",
        }

    async def clear_alerts(self, **kwargs) -> Dict[str, Any]:
        """Xóa tất cả alerts và history."""
        self._manager.clear_all()
        return {
            "success": True,
            "message": "Đã xóa tất cả alerts và lịch sử.",
        }

    # =================================================================
    # HELPER METHODS
    # =================================================================

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Lấy giá hiện tại của cổ phiếu."""
        try:
            result = await self._data_tool.get_stock_price(
                symbol=symbol, interval="1D"
            )
            if result.get("success") and result.get("data"):
                data = result["data"]
                if isinstance(data, list) and len(data) > 0:
                    return data[-1].get("close")
                elif isinstance(data, dict):
                    # DataFrame converted to dict
                    prices = data.get("close", {})
                    if prices:
                        last_key = max(prices.keys()) if isinstance(prices, dict) else -1
                        return prices.get(last_key)
            return None
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
            return None

    async def _get_rsi(self, symbol: str, period: int = 14) -> Optional[float]:
        """Tính RSI hiện tại."""
        try:
            from dexter_vietnam.tools.vietnam.technical.indicators import TechnicalIndicatorsTool
            tech_tool = TechnicalIndicatorsTool()
            result = await tech_tool.run(
                action="rsi", symbol=symbol, period=period, last_n=1
            )
            if result.get("success"):
                data = result.get("data", {})
                latest = data.get("latest", {})
                return latest.get("rsi") or latest.get("RSI")
            return None
        except Exception as e:
            logger.warning(f"Failed to get RSI for {symbol}: {e}")
            return None

    async def _get_volume_ratio(self, symbol: str, avg_days: int = 20) -> Optional[float]:
        """Tính tỷ lệ volume hôm nay / trung bình avg_days phiên."""
        try:
            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=avg_days * 2)).strftime("%Y-%m-%d")
            result = await self._data_tool.get_stock_price(
                symbol=symbol, start=start, end=end
            )
            if result.get("success") and result.get("data"):
                data = result["data"]
                if isinstance(data, list) and len(data) >= 2:
                    volumes = [d.get("volume", 0) for d in data]
                    if len(volumes) >= avg_days + 1:
                        avg_vol = sum(volumes[-(avg_days + 1):-1]) / avg_days
                        if avg_vol > 0:
                            return volumes[-1] / avg_vol
            return None
        except Exception as e:
            logger.warning(f"Failed to get volume ratio for {symbol}: {e}")
            return None
