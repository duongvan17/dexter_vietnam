"""
Module 15: Social / Community — Cộng đồng đầu tư

Theo CODING_ROADMAP.md - Module 15:
- get_top_portfolios(): Top danh mục hiệu quả
- get_leaderboard(): Bảng xếp hạng nhà đầu tư
- share_portfolio(portfolio_id): Chia sẻ danh mục

Mở rộng:
- create_portfolio(): Tạo danh mục theo dõi
- add_holding(): Thêm CP vào danh mục
- portfolio_performance(): Tính hiệu suất danh mục
- watchlist(): Danh sách theo dõi

Storage: JSON file (data/portfolios.json)
"""
from dexter_vietnam.tools.base import BaseTool
from typing import Dict, Any, Optional, List
import json
import os
import logging
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

# Default data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data")
PORTFOLIOS_FILE = os.path.join(DATA_DIR, "portfolios.json")


class PortfolioManager:
    """Quản lý danh mục đầu tư & cộng đồng — JSON storage."""

    def __init__(self, filepath: str = PORTFOLIOS_FILE):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            self._save({"portfolios": {}, "watchlists": {}})

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"portfolios": {}, "watchlists": {}}

    def _save(self, data: Dict[str, Any]):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    # --- Portfolio CRUD ---

    def create_portfolio(
        self,
        name: str,
        description: str = "",
        owner: str = "default",
        is_public: bool = True,
    ) -> Dict[str, Any]:
        data = self._load()
        pid = str(uuid.uuid4())[:8]
        portfolio = {
            "id": pid,
            "name": name,
            "description": description,
            "owner": owner,
            "is_public": is_public,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "holdings": [],
            "initial_capital": 0,
            "cash": 0,
        }
        data["portfolios"][pid] = portfolio
        self._save(data)
        return portfolio

    def add_holding(
        self,
        portfolio_id: str,
        symbol: str,
        quantity: int,
        buy_price: float,
        buy_date: str = "",
    ) -> Optional[Dict[str, Any]]:
        data = self._load()
        if portfolio_id not in data["portfolios"]:
            return None

        holding = {
            "symbol": symbol.upper(),
            "quantity": quantity,
            "buy_price": buy_price,
            "buy_date": buy_date or datetime.now().strftime("%Y-%m-%d"),
            "added_at": datetime.now().isoformat(),
        }
        data["portfolios"][portfolio_id]["holdings"].append(holding)
        data["portfolios"][portfolio_id]["updated_at"] = datetime.now().isoformat()
        self._save(data)
        return data["portfolios"][portfolio_id]

    def remove_holding(
        self,
        portfolio_id: str,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        data = self._load()
        if portfolio_id not in data["portfolios"]:
            return None
        portfolio = data["portfolios"][portfolio_id]
        portfolio["holdings"] = [
            h for h in portfolio["holdings"]
            if h["symbol"] != symbol.upper()
        ]
        portfolio["updated_at"] = datetime.now().isoformat()
        self._save(data)
        return portfolio

    def get_portfolio(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        return data["portfolios"].get(portfolio_id)

    def list_portfolios(self, owner: str = "") -> List[Dict[str, Any]]:
        data = self._load()
        portfolios = list(data["portfolios"].values())
        if owner:
            portfolios = [p for p in portfolios if p["owner"] == owner]
        return portfolios

    def delete_portfolio(self, portfolio_id: str) -> bool:
        data = self._load()
        if portfolio_id in data["portfolios"]:
            del data["portfolios"][portfolio_id]
            self._save(data)
            return True
        return False

    # --- Watchlist ---

    def add_to_watchlist(self, symbol: str, owner: str = "default", note: str = "") -> Dict:
        data = self._load()
        if owner not in data["watchlists"]:
            data["watchlists"][owner] = []

        # Check duplicate
        existing = [w for w in data["watchlists"][owner] if w["symbol"] == symbol.upper()]
        if existing:
            return {"added": False, "reason": "Đã có trong watchlist"}

        entry = {
            "symbol": symbol.upper(),
            "note": note,
            "added_at": datetime.now().isoformat(),
        }
        data["watchlists"][owner].append(entry)
        self._save(data)
        return {"added": True, "entry": entry}

    def remove_from_watchlist(self, symbol: str, owner: str = "default") -> bool:
        data = self._load()
        if owner not in data["watchlists"]:
            return False
        before = len(data["watchlists"][owner])
        data["watchlists"][owner] = [
            w for w in data["watchlists"][owner]
            if w["symbol"] != symbol.upper()
        ]
        if len(data["watchlists"][owner]) < before:
            self._save(data)
            return True
        return False

    def get_watchlist(self, owner: str = "default") -> List[Dict]:
        data = self._load()
        return data["watchlists"].get(owner, [])


# =====================================================================
# SAMPLE DATA — Danh mục mẫu cho demo / leaderboard
# =====================================================================

SAMPLE_PORTFOLIOS = [
    {
        "rank": 1,
        "name": "🏆 Blue-Chip Champion",
        "owner": "demo_user_1",
        "strategy": "Value Investing",
        "description": "Tập trung vào cổ phiếu blue-chip, ROE cao, cổ tức ổn định",
        "holdings": [
            {"symbol": "VCB", "weight": "25%", "buy_price": 75.0, "current_est": 92.0},
            {"symbol": "FPT", "weight": "20%", "buy_price": 85.0, "current_est": 130.0},
            {"symbol": "VNM", "weight": "20%", "buy_price": 72.0, "current_est": 78.0},
            {"symbol": "MWG", "weight": "15%", "buy_price": 48.0, "current_est": 62.0},
            {"symbol": "ACB", "weight": "10%", "buy_price": 22.0, "current_est": 27.0},
            {"symbol": "Cash", "weight": "10%", "buy_price": 0, "current_est": 0},
        ],
        "ytd_return": "+28.5%",
        "sharpe_ratio": 1.85,
        "max_drawdown": "-8.2%",
        "win_rate": "72%",
    },
    {
        "rank": 2,
        "name": "📈 Growth Hunter",
        "owner": "demo_user_2",
        "strategy": "Growth Investing",
        "description": "Cổ phiếu tăng trưởng cao, công nghệ & bán lẻ",
        "holdings": [
            {"symbol": "FPT", "weight": "30%", "buy_price": 90.0, "current_est": 130.0},
            {"symbol": "MWG", "weight": "20%", "buy_price": 45.0, "current_est": 62.0},
            {"symbol": "PNJ", "weight": "15%", "buy_price": 78.0, "current_est": 95.0},
            {"symbol": "TCB", "weight": "20%", "buy_price": 28.0, "current_est": 36.0},
            {"symbol": "VHM", "weight": "15%", "buy_price": 42.0, "current_est": 48.0},
        ],
        "ytd_return": "+32.1%",
        "sharpe_ratio": 1.62,
        "max_drawdown": "-12.5%",
        "win_rate": "65%",
    },
    {
        "rank": 3,
        "name": "🛡️ Dividend Shield",
        "owner": "demo_user_3",
        "strategy": "Dividend Investing",
        "description": "Cổ tức cao, ổn định, phòng thủ",
        "holdings": [
            {"symbol": "VNM", "weight": "25%", "buy_price": 70.0, "current_est": 78.0},
            {"symbol": "GAS", "weight": "20%", "buy_price": 85.0, "current_est": 95.0},
            {"symbol": "BVH", "weight": "15%", "buy_price": 45.0, "current_est": 52.0},
            {"symbol": "REE", "weight": "20%", "buy_price": 55.0, "current_est": 62.0},
            {"symbol": "PHR", "weight": "10%", "buy_price": 55.0, "current_est": 60.0},
            {"symbol": "Cash", "weight": "10%", "buy_price": 0, "current_est": 0},
        ],
        "ytd_return": "+15.8%",
        "sharpe_ratio": 2.10,
        "max_drawdown": "-5.3%",
        "win_rate": "78%",
    },
    {
        "rank": 4,
        "name": "⚡ Swing Master",
        "owner": "demo_user_4",
        "strategy": "Swing Trading",
        "description": "Giao dịch ngắn hạn kết hợp kỹ thuật & dòng tiền",
        "holdings": [
            {"symbol": "HPG", "weight": "20%", "buy_price": 24.0, "current_est": 28.0},
            {"symbol": "SSI", "weight": "20%", "buy_price": 28.0, "current_est": 33.0},
            {"symbol": "STB", "weight": "15%", "buy_price": 25.0, "current_est": 30.0},
            {"symbol": "VPB", "weight": "15%", "buy_price": 18.0, "current_est": 22.0},
            {"symbol": "Cash", "weight": "30%", "buy_price": 0, "current_est": 0},
        ],
        "ytd_return": "+22.3%",
        "sharpe_ratio": 1.45,
        "max_drawdown": "-14.1%",
        "win_rate": "58%",
    },
    {
        "rank": 5,
        "name": "🏦 Banking Focus",
        "owner": "demo_user_5",
        "strategy": "Sector Investing — Banking",
        "description": "Tập trung ngành ngân hàng, hưởng lợi từ tín dụng tăng",
        "holdings": [
            {"symbol": "VCB", "weight": "25%", "buy_price": 78.0, "current_est": 92.0},
            {"symbol": "TCB", "weight": "20%", "buy_price": 26.0, "current_est": 36.0},
            {"symbol": "ACB", "weight": "20%", "buy_price": 21.0, "current_est": 27.0},
            {"symbol": "MBB", "weight": "20%", "buy_price": 18.0, "current_est": 24.0},
            {"symbol": "CTG", "weight": "15%", "buy_price": 28.0, "current_est": 35.0},
        ],
        "ytd_return": "+26.7%",
        "sharpe_ratio": 1.72,
        "max_drawdown": "-10.8%",
        "win_rate": "70%",
    },
]


class SocialTool(BaseTool):
    """
    Cộng đồng đầu tư — Quản lý danh mục, bảng xếp hạng, chia sẻ:
    - Xem top danh mục hiệu quả (mẫu)
    - Bảng xếp hạng nhà đầu tư
    - Tạo & quản lý danh mục cá nhân
    - Watchlist theo dõi mã CK
    """

    def __init__(self):
        self.manager = PortfolioManager()

    def get_name(self) -> str:
        return "social"

    def get_description(self) -> str:
        return (
            "Cộng đồng đầu tư: xem top danh mục mẫu, bảng xếp hạng, "
            "tạo & quản lý danh mục cá nhân, watchlist theo dõi mã CP. "
            "Actions: top_portfolios, leaderboard, create_portfolio, "
            "add_holding, remove_holding, my_portfolios, portfolio_detail, "
            "delete_portfolio, watchlist, add_watchlist, remove_watchlist."
        )

    async def run(self, action: str = "top_portfolios", **kwargs) -> Dict[str, Any]:
        action_map = {
            "top_portfolios": self.get_top_portfolios,
            "leaderboard": self.get_leaderboard,
            "create_portfolio": self.create_portfolio,
            "add_holding": self.add_holding,
            "remove_holding": self.remove_holding,
            "my_portfolios": self.list_my_portfolios,
            "portfolio_detail": self.get_portfolio_detail,
            "delete_portfolio": self.delete_portfolio,
            "watchlist": self.get_watchlist,
            "add_watchlist": self.add_to_watchlist,
            "remove_watchlist": self.remove_from_watchlist,
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
            logger.error(f"Social '{action}' failed: {e}", exc_info=True)
            return {"success": False, "error": f"Lỗi: {str(e)}"}

    # =================================================================
    # 1. TOP PORTFOLIOS — Danh mục mẫu hiệu quả
    # =================================================================

    async def get_top_portfolios(
        self,
        top_n: int = 5,
        sort_by: str = "return",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Xem top danh mục đầu tư hiệu quả (mẫu).

        Args:
            top_n: Số danh mục hiển thị (mặc định 5)
            sort_by: Sắp xếp theo 'return', 'sharpe', 'drawdown'
        """
        portfolios = SAMPLE_PORTFOLIOS.copy()

        if sort_by == "sharpe":
            portfolios.sort(key=lambda x: x["sharpe_ratio"], reverse=True)
        elif sort_by == "drawdown":
            portfolios.sort(
                key=lambda x: float(x["max_drawdown"].replace("%", "")),
                reverse=True,  # least negative = best
            )
        # default: keep rank order (by return)

        portfolios = portfolios[:top_n]

        summary_parts = ["## 🏆 Top Danh mục Đầu tư Hiệu quả\n"]
        for p in portfolios:
            summary_parts.append(
                f"### #{p['rank']} {p['name']}\n"
                f"📋 Chiến lược: {p['strategy']}\n"
                f"📝 {p['description']}\n"
                f"📊 YTD: **{p['ytd_return']}** | Sharpe: {p['sharpe_ratio']} | "
                f"Max DD: {p['max_drawdown']} | Win: {p['win_rate']}\n"
                f"💼 Holdings: {', '.join(h['symbol'] + ' (' + h['weight'] + ')' for h in p['holdings'])}\n"
            )

        return {
            "success": True,
            "data": {
                "portfolios": portfolios,
                "total": len(portfolios),
                "sort_by": sort_by,
            },
            "summary": "\n".join(summary_parts),
        }

    # =================================================================
    # 2. LEADERBOARD — Bảng xếp hạng
    # =================================================================

    async def get_leaderboard(
        self,
        period: str = "ytd",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Bảng xếp hạng nhà đầu tư.

        Args:
            period: Kỳ xếp hạng (ytd, 1m, 3m, 6m, 1y)
        """
        # Simulated leaderboard from sample data
        leaderboard = []
        for p in SAMPLE_PORTFOLIOS:
            leaderboard.append({
                "rank": p["rank"],
                "name": p["name"],
                "owner": p["owner"],
                "strategy": p["strategy"],
                "return": p["ytd_return"],
                "sharpe": p["sharpe_ratio"],
                "max_drawdown": p["max_drawdown"],
                "win_rate": p["win_rate"],
                "num_holdings": len([h for h in p["holdings"] if h["symbol"] != "Cash"]),
            })

        summary_parts = [f"## 🥇 Bảng xếp hạng — {period.upper()}\n"]
        summary_parts.append("| Rank | Tên | Chiến lược | Return | Sharpe | Max DD | Win |")
        summary_parts.append("|------|-----|-----------|--------|--------|--------|-----|")
        for r in leaderboard:
            summary_parts.append(
                f"| #{r['rank']} | {r['name']} | {r['strategy']} | "
                f"**{r['return']}** | {r['sharpe']} | {r['max_drawdown']} | {r['win_rate']} |"
            )

        # User portfolios
        user_portfolios = self.manager.list_portfolios()
        if user_portfolios:
            summary_parts.append(f"\n📌 Bạn có {len(user_portfolios)} danh mục cá nhân. "
                                 "Dùng action 'my_portfolios' để xem.")

        return {
            "success": True,
            "data": {
                "period": period,
                "leaderboard": leaderboard,
                "total": len(leaderboard),
                "user_portfolios_count": len(user_portfolios),
            },
            "summary": "\n".join(summary_parts),
        }

    # =================================================================
    # 3. CREATE PORTFOLIO — Tạo danh mục
    # =================================================================

    async def create_portfolio(
        self,
        name: str = "Danh mục mới",
        description: str = "",
        owner: str = "default",
        is_public: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Tạo danh mục đầu tư mới.

        Args:
            name: Tên danh mục
            description: Mô tả
            owner: Chủ sở hữu
            is_public: Công khai? (True/False)
        """
        portfolio = self.manager.create_portfolio(
            name=name,
            description=description,
            owner=owner,
            is_public=is_public,
        )

        return {
            "success": True,
            "data": portfolio,
            "summary": (
                f"✅ Đã tạo danh mục **{name}** (ID: `{portfolio['id']}`). "
                f"Dùng action 'add_holding' với portfolio_id='{portfolio['id']}' "
                f"để thêm cổ phiếu."
            ),
        }

    # =================================================================
    # 4. ADD HOLDING — Thêm CP vào danh mục
    # =================================================================

    async def add_holding(
        self,
        portfolio_id: str = "",
        symbol: str = "",
        quantity: int = 100,
        buy_price: float = 0,
        buy_date: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Thêm cổ phiếu vào danh mục.

        Args:
            portfolio_id: ID danh mục
            symbol: Mã CP
            quantity: Số lượng
            buy_price: Giá mua (nghìn VND)
            buy_date: Ngày mua (YYYY-MM-DD)
        """
        if not portfolio_id:
            return {"success": False, "error": "Cần portfolio_id."}
        if not symbol:
            return {"success": False, "error": "Cần mã CP (symbol)."}

        result = self.manager.add_holding(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=quantity,
            buy_price=buy_price,
            buy_date=buy_date,
        )

        if result is None:
            return {"success": False, "error": f"Không tìm thấy danh mục ID '{portfolio_id}'."}

        holdings_count = len(result["holdings"])
        return {
            "success": True,
            "data": result,
            "summary": (
                f"✅ Đã thêm {quantity:,} {symbol.upper()} (giá {buy_price}) "
                f"vào danh mục **{result['name']}**. "
                f"Tổng: {holdings_count} vị thế."
            ),
        }

    # =================================================================
    # 5. REMOVE HOLDING — Xoá CP khỏi danh mục
    # =================================================================

    async def remove_holding(
        self,
        portfolio_id: str = "",
        symbol: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Xoá CP khỏi danh mục.

        Args:
            portfolio_id: ID danh mục
            symbol: Mã CP cần xoá
        """
        if not portfolio_id or not symbol:
            return {"success": False, "error": "Cần portfolio_id và symbol."}

        result = self.manager.remove_holding(portfolio_id, symbol)
        if result is None:
            return {"success": False, "error": f"Không tìm thấy danh mục ID '{portfolio_id}'."}

        return {
            "success": True,
            "data": result,
            "summary": f"✅ Đã xoá {symbol.upper()} khỏi danh mục **{result['name']}**.",
        }

    # =================================================================
    # 6. MY PORTFOLIOS — Danh sách danh mục cá nhân
    # =================================================================

    async def list_my_portfolios(
        self,
        owner: str = "default",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Liệt kê danh mục cá nhân.

        Args:
            owner: Chủ sở hữu (mặc định 'default')
        """
        portfolios = self.manager.list_portfolios(owner=owner)

        if not portfolios:
            return {
                "success": True,
                "data": {"portfolios": [], "total": 0},
                "summary": (
                    "📭 Chưa có danh mục nào. "
                    "Dùng action 'create_portfolio' để tạo mới."
                ),
            }

        summary_parts = [f"## 📁 Danh mục của bạn ({len(portfolios)})\n"]
        for p in portfolios:
            holdings_str = ", ".join(
                h["symbol"] for h in p.get("holdings", [])
            ) or "Chưa có CP"
            summary_parts.append(
                f"### 📋 {p['name']} (ID: `{p['id']}`)\n"
                f"📝 {p.get('description', '')}\n"
                f"💼 {len(p.get('holdings', []))} vị thế: {holdings_str}\n"
                f"📅 Cập nhật: {p.get('updated_at', 'N/A')}\n"
            )

        return {
            "success": True,
            "data": {"portfolios": portfolios, "total": len(portfolios)},
            "summary": "\n".join(summary_parts),
        }

    # =================================================================
    # 7. PORTFOLIO DETAIL — Chi tiết danh mục
    # =================================================================

    async def get_portfolio_detail(
        self,
        portfolio_id: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Xem chi tiết danh mục.

        Args:
            portfolio_id: ID danh mục
        """
        if not portfolio_id:
            return {"success": False, "error": "Cần portfolio_id."}

        portfolio = self.manager.get_portfolio(portfolio_id)
        if not portfolio:
            return {"success": False, "error": f"Không tìm thấy danh mục ID '{portfolio_id}'."}

        holdings = portfolio.get("holdings", [])

        # Calculate basic stats
        total_cost = sum(
            h["quantity"] * h["buy_price"] * 1000
            for h in holdings
        )

        summary_parts = [
            f"## 📋 {portfolio['name']}\n",
            f"📝 {portfolio.get('description', '')}",
            f"👤 Owner: {portfolio.get('owner', 'N/A')}",
            f"📅 Tạo: {portfolio.get('created_at', 'N/A')}",
            f"🔄 Cập nhật: {portfolio.get('updated_at', 'N/A')}",
            f"\n### 💼 Holdings ({len(holdings)} vị thế)\n",
        ]

        if holdings:
            summary_parts.append("| Mã | SL | Giá mua | Giá trị | Ngày mua |")
            summary_parts.append("|----|----|---------|---------|----------|")
            for h in holdings:
                value = h["quantity"] * h["buy_price"] * 1000
                summary_parts.append(
                    f"| {h['symbol']} | {h['quantity']:,} | "
                    f"{h['buy_price']} | {value / 1e6:,.1f}M | {h.get('buy_date', 'N/A')} |"
                )
            summary_parts.append(f"\n💰 Tổng chi phí: **{total_cost / 1e6:,.1f}M VND**")
        else:
            summary_parts.append("_Chưa có cổ phiếu nào._")

        summary_parts.append(
            f"\n💡 Dùng 'phân tích [MÃ CP]' để phân tích từng CP trong danh mục."
        )

        return {
            "success": True,
            "data": {
                "portfolio": portfolio,
                "total_cost": round(total_cost),
                "num_holdings": len(holdings),
            },
            "summary": "\n".join(summary_parts),
        }

    # =================================================================
    # 8. DELETE PORTFOLIO — Xoá danh mục
    # =================================================================

    async def delete_portfolio(
        self,
        portfolio_id: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Xoá danh mục.

        Args:
            portfolio_id: ID danh mục cần xoá
        """
        if not portfolio_id:
            return {"success": False, "error": "Cần portfolio_id."}

        deleted = self.manager.delete_portfolio(portfolio_id)
        if not deleted:
            return {"success": False, "error": f"Không tìm thấy danh mục ID '{portfolio_id}'."}

        return {
            "success": True,
            "data": {"deleted_id": portfolio_id},
            "summary": f"🗑️ Đã xoá danh mục ID `{portfolio_id}`.",
        }

    # =================================================================
    # 9. WATCHLIST — Danh sách theo dõi
    # =================================================================

    async def get_watchlist(
        self,
        owner: str = "default",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Xem watchlist (danh sách CP đang theo dõi).

        Args:
            owner: Chủ sở hữu
        """
        watchlist = self.manager.get_watchlist(owner)

        if not watchlist:
            return {
                "success": True,
                "data": {"watchlist": [], "total": 0},
                "summary": (
                    "📭 Watchlist trống. "
                    "Dùng action 'add_watchlist' để thêm mã CP theo dõi."
                ),
            }

        summary_parts = [f"## 👁️ Watchlist ({len(watchlist)} mã)\n"]
        for i, w in enumerate(watchlist, 1):
            note = f" — {w['note']}" if w.get("note") else ""
            summary_parts.append(
                f"{i}. **{w['symbol']}**{note} (thêm: {w['added_at'][:10]})"
            )

        summary_parts.append(
            f"\n💡 Dùng 'phân tích [MÃ]' để xem phân tích chi tiết."
        )

        return {
            "success": True,
            "data": {"watchlist": watchlist, "total": len(watchlist)},
            "summary": "\n".join(summary_parts),
        }

    # =================================================================
    # 10. ADD WATCHLIST — Thêm vào watchlist
    # =================================================================

    async def add_to_watchlist(
        self,
        symbol: str = "",
        owner: str = "default",
        note: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Thêm mã CP vào watchlist.

        Args:
            symbol: Mã CP
            owner: Chủ sở hữu
            note: Ghi chú
        """
        if not symbol:
            return {"success": False, "error": "Cần mã CP (symbol)."}

        result = self.manager.add_to_watchlist(symbol, owner, note)

        if result.get("added"):
            return {
                "success": True,
                "data": result,
                "summary": f"✅ Đã thêm **{symbol.upper()}** vào watchlist."
                           + (f" Note: {note}" if note else ""),
            }
        else:
            return {
                "success": True,
                "data": result,
                "summary": f"⚠️ {symbol.upper()} {result.get('reason', 'đã tồn tại')}.",
            }

    # =================================================================
    # 11. REMOVE WATCHLIST — Xoá khỏi watchlist
    # =================================================================

    async def remove_from_watchlist(
        self,
        symbol: str = "",
        owner: str = "default",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Xoá mã CP khỏi watchlist.

        Args:
            symbol: Mã CP cần xoá
            owner: Chủ sở hữu
        """
        if not symbol:
            return {"success": False, "error": "Cần mã CP (symbol)."}

        removed = self.manager.remove_from_watchlist(symbol, owner)

        if removed:
            return {
                "success": True,
                "data": {"removed": symbol.upper()},
                "summary": f"🗑️ Đã xoá **{symbol.upper()}** khỏi watchlist.",
            }
        else:
            return {
                "success": False,
                "error": f"Không tìm thấy {symbol.upper()} trong watchlist.",
            }
