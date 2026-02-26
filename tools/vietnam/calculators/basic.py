
from dexter_vietnam.tools.base import BaseTool
from typing import Dict, Any, Optional, List
import math
import logging

logger = logging.getLogger(__name__)

VN_SELL_TAX_RATE = 0.001          # Thuế bán 0.1% trên giá trị bán
VN_BROKER_FEE_DEFAULT = 0.0015   # Phí môi giới mặc định 0.15%
VN_PERSONAL_INCOME_TAX = 0.001   # Thuế TNCN 0.1% trên giá trị bán (đã gộp trong sell tax)
VN_LOT_SIZE = 100                # 1 lô = 100 cổ phiếu


class CalculatorsTool(BaseTool):

    def get_name(self) -> str:
        return "calculators"

    def get_description(self) -> str:
        return (
            "Công cụ tính toán tài chính: lãi kép, position sizing "
            "(khối lượng vào lệnh), thuế & phí giao dịch CK Việt Nam, "
            "giá hoà vốn, margin, DCA. "
        )

    def get_actions(self) -> dict:
        return {
            "compound_interest": "Tính lãi kép: số tiền cuối kỳ, lãi suất, số năm",
            "position_sizing": "Tính khối lượng vào lệnh theo % rủi ro, stop-loss",
            "tax": "Tính thuế + phí giao dịch chứng khoán Việt Nam (0.1% thuế bán)",
            "breakeven": "Tính giá hoà vốn sau khi tính phí mua/bán",
            "margin": "Tính margin call, tỷ lệ đòn bẩy",
            "dca": "Tính DCA (Dollar Cost Averaging): giá vốn bình quân",
        }


    async def run(self, action: str = "compound_interest", **kwargs) -> Dict[str, Any]:

        action_map = {
            "compound_interest": self.calculate_compound_interest,
            "position_sizing": self.calculate_position_sizing,
            "tax": self.calculate_tax,
            "breakeven": self.calculate_breakeven,
            "margin": self.calculate_margin,
            "dca": self.calculate_dca,
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
            logger.error(f"Calculator '{action}' failed: {e}", exc_info=True)
            return {"success": False, "error": f"Lỗi tính toán: {str(e)}"}


    async def calculate_compound_interest(
        self,
        principal: float = 100_000_000,
        annual_rate: float = 0.10,
        years: int = 10,
        monthly_contribution: float = 0,
        compounds_per_year: int = 12,
        **kwargs,
    ) -> Dict[str, Any]:

        n = compounds_per_year
        r = annual_rate
        t = years
        pmt = monthly_contribution

        # Future Value of principal
        fv_principal = principal * (1 + r / n) ** (n * t)

        # Future Value of monthly contributions (annuity)
        fv_contributions = 0
        if pmt > 0:
            total_periods = n * t
            rate_per_period = r / n
            if rate_per_period > 0:
                fv_contributions = pmt * (((1 + rate_per_period) ** total_periods - 1) / rate_per_period)
            else:
                fv_contributions = pmt * total_periods

        total_future_value = fv_principal + fv_contributions
        total_contributed = principal + (pmt * 12 * t)
        total_interest = total_future_value - total_contributed

        # Year-by-year breakdown
        yearly_breakdown = []
        balance = principal
        for year in range(1, t + 1):
            year_start = balance
            for _ in range(n):
                balance = balance * (1 + r / n) + (pmt if n == 12 else pmt * 12 / n)
            interest_earned = balance - year_start - (pmt * 12)
            yearly_breakdown.append({
                "year": year,
                "balance": round(balance),
                "interest_earned": round(interest_earned),
                "total_contributed": round(principal + pmt * 12 * year),
            })

        return {
            "success": True,
            "data": {
                "principal": principal,
                "annual_rate": f"{annual_rate * 100:.1f}%",
                "years": years,
                "monthly_contribution": monthly_contribution,
                "compounds_per_year": compounds_per_year,
                "future_value": round(total_future_value),
                "total_contributed": round(total_contributed),
                "total_interest": round(total_interest),
                "interest_ratio": f"{(total_interest / total_contributed * 100):.1f}%",
                "yearly_breakdown": yearly_breakdown,
            },
            "summary": (
                f"Đầu tư {principal / 1e6:,.0f}M"
                f"{f' + {pmt / 1e6:,.1f}M/tháng' if pmt > 0 else ''}, "
                f"lãi suất {annual_rate * 100:.1f}%/năm, sau {years} năm: "
                f"**{total_future_value / 1e6:,.0f}M VND** "
                f"(lãi {total_interest / 1e6:,.0f}M)"
            ),
        }


    async def calculate_position_sizing(
        self,
        capital: float = 100_000_000,
        risk_percent: float = 2.0,
        entry_price: float = 50.0,
        stop_loss_price: float = 47.0,
        broker_fee: float = VN_BROKER_FEE_DEFAULT,
        **kwargs,
    ) -> Dict[str, Any]:

        if entry_price <= 0:
            return {"success": False, "error": "entry_price phải > 0"}
        if stop_loss_price >= entry_price:
            return {"success": False, "error": "stop_loss_price phải < entry_price"}

        # Risk per share (nghìn VND → VND)
        risk_per_share = (entry_price - stop_loss_price) * 1000
        max_risk_amount = capital * (risk_percent / 100)

        # Max shares based on risk
        max_shares = int(max_risk_amount / risk_per_share)
        # Round down to lot size
        max_lots = max_shares // VN_LOT_SIZE
        max_shares_rounded = max_lots * VN_LOT_SIZE

        # Position value
        position_value = max_shares_rounded * entry_price * 1000
        # Fees
        buy_fee = position_value * broker_fee
        sell_fee = position_value * broker_fee
        sell_tax = position_value * VN_SELL_TAX_RATE
        total_fees = buy_fee + sell_fee + sell_tax

        # Actual risk
        actual_loss_if_sl = max_shares_rounded * risk_per_share
        actual_risk_pct = (actual_loss_if_sl / capital) * 100

        # Risk/Reward scenarios
        risk_amount = entry_price - stop_loss_price
        rr_2to1_target = entry_price + (risk_amount * 2)
        rr_3to1_target = entry_price + (risk_amount * 3)
        profit_2to1 = max_shares_rounded * risk_amount * 2 * 1000 - total_fees
        profit_3to1 = max_shares_rounded * risk_amount * 3 * 1000 - total_fees

        return {
            "success": True,
            "data": {
                "capital": capital,
                "risk_percent": f"{risk_percent}%",
                "max_risk_amount": round(max_risk_amount),
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
                "risk_per_share": risk_per_share,
                "max_shares": max_shares_rounded,
                "max_lots": max_lots,
                "position_value": round(position_value),
                "position_pct_of_capital": f"{position_value / capital * 100:.1f}%",
                "fees": {
                    "buy_fee": round(buy_fee),
                    "sell_fee": round(sell_fee),
                    "sell_tax": round(sell_tax),
                    "total_fees": round(total_fees),
                },
                "actual_risk": {
                    "loss_if_stop_loss": round(actual_loss_if_sl),
                    "risk_pct": f"{actual_risk_pct:.1f}%",
                },
                "risk_reward": {
                    "r2_target": rr_2to1_target,
                    "r2_profit": round(profit_2to1),
                    "r3_target": rr_3to1_target,
                    "r3_profit": round(profit_3to1),
                },
            },
            "summary": (
                f"Vốn {capital / 1e6:,.0f}M, rủi ro {risk_percent}% → "
                f"Mua tối đa **{max_shares_rounded:,} cổ** ({max_lots} lô) "
                f"tại giá {entry_price}, SL: {stop_loss_price}. "
                f"Giá trị lệnh: {position_value / 1e6:,.1f}M. "
                f"R:R 2:1 target = {rr_2to1_target}"
            ),
        }

    async def calculate_tax(
        self,
        buy_price: float = 50.0,
        sell_price: float = 55.0,
        quantity: int = 1000,
        broker_fee: float = VN_BROKER_FEE_DEFAULT,
        **kwargs,
    ) -> Dict[str, Any]:

        buy_value = quantity * buy_price * 1000    # VND
        sell_value = quantity * sell_price * 1000

        fee_buy = buy_value * broker_fee
        fee_sell = sell_value * broker_fee
        tax_sell = sell_value * VN_SELL_TAX_RATE
        total_fees = fee_buy + fee_sell + tax_sell

        gross_profit = sell_value - buy_value
        net_profit = gross_profit - total_fees
        net_profit_pct = (net_profit / buy_value * 100) if buy_value > 0 else 0

        # Breakeven sell price (to cover buy fees + sell fees + sell tax)
        # sell_value - buy_value - fee_buy - fee_sell - tax_sell = 0
        # sell_value * (1 - broker_fee - 0.001) = buy_value * (1 + broker_fee)
        be_sell_value = buy_value * (1 + broker_fee) / (1 - broker_fee - VN_SELL_TAX_RATE)
        breakeven_price = be_sell_value / (quantity * 1000) if quantity > 0 else 0

        return {
            "success": True,
            "data": {
                "buy_price": buy_price,
                "sell_price": sell_price,
                "quantity": quantity,
                "buy_value": round(buy_value),
                "sell_value": round(sell_value),
                "fees": {
                    "broker_fee_buy": round(fee_buy),
                    "broker_fee_sell": round(fee_sell),
                    "sell_tax": round(tax_sell),
                    "total_fees": round(total_fees),
                    "fee_pct_of_buy": f"{total_fees / buy_value * 100:.2f}%",
                },
                "gross_profit": round(gross_profit),
                "net_profit": round(net_profit),
                "net_profit_pct": f"{net_profit_pct:.2f}%",
                "breakeven_sell_price": round(breakeven_price, 2),
                "is_profitable": net_profit > 0,
            },
            "summary": (
                f"Mua {quantity:,} CP tại {buy_price}, bán tại {sell_price}. "
                f"Phí tổng: {total_fees / 1e3:,.0f}K. "
                f"Lãi ròng: **{net_profit / 1e6:,.2f}M VND** ({net_profit_pct:+.2f}%). "
                f"Giá hoà vốn: {breakeven_price:,.2f}"
            ),
        }


    async def calculate_breakeven(
        self,
        buy_price: float = 50.0,
        quantity: int = 1000,
        broker_fee: float = VN_BROKER_FEE_DEFAULT,
        additional_buys: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:

        # Tính tổng cost bao gồm phí
        buys = [{"price": buy_price, "quantity": quantity}]
        if additional_buys:
            buys.extend(additional_buys)

        total_quantity = 0
        total_cost = 0  # Bao gồm phí mua

        buy_details = []
        for i, b in enumerate(buys):
            p = b["price"]
            q = b["quantity"]
            value = p * q * 1000
            fee = value * broker_fee
            cost = value + fee

            total_quantity += q
            total_cost += cost

            buy_details.append({
                "buy_number": i + 1,
                "price": p,
                "quantity": q,
                "value": round(value),
                "fee": round(fee),
                "total_cost": round(cost),
            })

        # Average cost per share (đã gồm phí mua)
        avg_cost_per_share = total_cost / (total_quantity * 1000) if total_quantity > 0 else 0

        # Breakeven sell price (phải cover phí bán + thuế bán nữa)
        # net = sell_value * (1 - broker_fee - sell_tax) - total_cost = 0
        breakeven_sell_price = total_cost / (total_quantity * 1000 * (1 - broker_fee - VN_SELL_TAX_RATE)) if total_quantity > 0 else 0

        return {
            "success": True,
            "data": {
                "buy_details": buy_details,
                "total_quantity": total_quantity,
                "total_lots": total_quantity // VN_LOT_SIZE,
                "total_cost": round(total_cost),
                "avg_cost_per_share": round(avg_cost_per_share, 2),
                "breakeven_sell_price": round(breakeven_sell_price, 2),
                "note": "Giá hoà vốn đã tính phí mua + phí bán + thuế bán 0.1%",
            },
            "summary": (
                f"Tổng {total_quantity:,} CP, chi phí {total_cost / 1e6:,.1f}M (gồm phí). "
                f"Giá TB: {avg_cost_per_share:,.2f}. "
                f"**Giá hoà vốn (bán)**: {breakeven_sell_price:,.2f}"
            ),
        }

    async def calculate_margin(
        self,
        equity: float = 100_000_000,
        margin_ratio: float = 50.0,
        entry_price: float = 50.0,
        quantity: int = 0,
        maintenance_rate: float = 30.0,
        interest_rate: float = 12.0,
        holding_days: int = 30,
        **kwargs,
    ) -> Dict[str, Any]:

        margin_pct = margin_ratio / 100
        maintenance_pct = maintenance_rate / 100

        # Buying power
        buying_power = equity / margin_pct if margin_pct > 0 else equity
        loan_amount = buying_power - equity

        # Max shares
        if quantity <= 0:
            max_shares = int(buying_power / (entry_price * 1000))
            max_shares = (max_shares // VN_LOT_SIZE) * VN_LOT_SIZE
            quantity = max_shares

        position_value = quantity * entry_price * 1000
        actual_loan = position_value - equity if position_value > equity else 0

        # Interest cost
        daily_interest = actual_loan * (interest_rate / 100) / 365
        total_interest = daily_interest * holding_days

        # Call margin price
        # maintenance_pct = (current_value - loan) / current_value
        # → current_value * (1 - maintenance_pct) = loan
        # → current_value = loan / (1 - maintenance_pct)
        if actual_loan > 0 and maintenance_pct < 1:
            call_margin_value = actual_loan / (1 - maintenance_pct)
            call_margin_price = call_margin_value / (quantity * 1000) if quantity > 0 else 0
            drop_to_call = ((entry_price - call_margin_price) / entry_price * 100) if entry_price > 0 else 0
        else:
            call_margin_price = 0
            drop_to_call = 0

        # Force sell price (equity = 0)
        force_sell_price = actual_loan / (quantity * 1000) if quantity > 0 else 0

        # Profit scenarios
        scenarios = []
        for pct_change in [-20, -10, -5, 0, 5, 10, 20]:
            new_price = entry_price * (1 + pct_change / 100)
            new_value = quantity * new_price * 1000
            pnl = new_value - position_value - total_interest
            pnl_on_equity = (pnl / equity * 100) if equity > 0 else 0
            scenarios.append({
                "price_change": f"{pct_change:+d}%",
                "price": round(new_price, 2),
                "pnl": round(pnl),
                "return_on_equity": f"{pnl_on_equity:+.1f}%",
            })

        return {
            "success": True,
            "data": {
                "equity": equity,
                "margin_ratio": f"{margin_ratio}%",
                "buying_power": round(buying_power),
                "entry_price": entry_price,
                "quantity": quantity,
                "position_value": round(position_value),
                "loan_amount": round(actual_loan),
                "leverage": f"{position_value / equity:.1f}x" if equity > 0 else "N/A",
                "interest": {
                    "rate": f"{interest_rate}%/năm",
                    "daily": round(daily_interest),
                    "total": round(total_interest),
                    "holding_days": holding_days,
                },
                "call_margin_price": round(call_margin_price, 2),
                "drop_to_call_margin": f"-{drop_to_call:.1f}%",
                "force_sell_price": round(force_sell_price, 2),
                "scenarios": scenarios,
            },
            "summary": (
                f"Vốn {equity / 1e6:,.0f}M, margin {margin_ratio}% → "
                f"Mua {quantity:,} CP tại {entry_price}, "
                f"vay {actual_loan / 1e6:,.1f}M. "
                f"Lãi margin {holding_days} ngày: {total_interest / 1e3:,.0f}K. "
                f"**Call margin tại {call_margin_price:,.2f}** (giảm {drop_to_call:.1f}%)"
            ),
        }

    async def calculate_dca(
        self,
        symbol: str = "",
        monthly_amount: float = 5_000_000,
        months: int = 12,
        prices: Optional[List[float]] = None,
        start_price: float = 50.0,
        volatility: float = 5.0,
        broker_fee: float = VN_BROKER_FEE_DEFAULT,
        **kwargs,
    ) -> Dict[str, Any]:

        # Generate simulated prices if not provided
        if not prices:
            import random
            random.seed(42)
            prices = [start_price]
            for _ in range(months - 1):
                change = random.uniform(-volatility, volatility) / 100
                new_price = prices[-1] * (1 + change)
                prices.append(round(new_price, 2))

        if len(prices) < months:
            # Extend with last price
            prices.extend([prices[-1]] * (months - len(prices)))

        # Calculate DCA
        total_shares = 0
        total_invested = 0
        total_fees = 0
        monthly_details = []

        for i in range(months):
            price = prices[i]
            value = monthly_amount
            fee = value * broker_fee
            net_value = value - fee
            shares_bought = int(net_value / (price * 1000))
            # Round to lot size
            shares_bought = (shares_bought // VN_LOT_SIZE) * VN_LOT_SIZE
            actual_cost = shares_bought * price * 1000 + fee

            total_shares += shares_bought
            total_invested += actual_cost
            total_fees += fee

            avg_price = (total_invested - total_fees) / (total_shares * 1000) if total_shares > 0 else price

            monthly_details.append({
                "month": i + 1,
                "price": price,
                "shares_bought": shares_bought,
                "cost": round(actual_cost),
                "total_shares": total_shares,
                "avg_price": round(avg_price, 2),
            })

        # Final calculations
        final_price = prices[-1]
        final_value = total_shares * final_price * 1000
        avg_cost_price = total_invested / (total_shares * 1000) if total_shares > 0 else 0
        pnl = final_value - total_invested
        pnl_pct = (pnl / total_invested * 100) if total_invested > 0 else 0

        # Compare with lump sum (all in at start)
        lump_sum_shares = int(monthly_amount * months / (prices[0] * 1000))
        lump_sum_shares = (lump_sum_shares // VN_LOT_SIZE) * VN_LOT_SIZE
        lump_sum_value = lump_sum_shares * final_price * 1000
        lump_sum_cost = lump_sum_shares * prices[0] * 1000
        lump_sum_pnl = lump_sum_value - lump_sum_cost

        return {
            "success": True,
            "data": {
                "symbol": symbol.upper() if symbol else "N/A",
                "monthly_amount": monthly_amount,
                "months": months,
                "total_shares": total_shares,
                "total_invested": round(total_invested),
                "total_fees": round(total_fees),
                "avg_cost_price": round(avg_cost_price, 2),
                "final_price": final_price,
                "final_value": round(final_value),
                "pnl": round(pnl),
                "pnl_pct": f"{pnl_pct:+.2f}%",
                "comparison": {
                    "dca_pnl": round(pnl),
                    "lump_sum_pnl": round(lump_sum_pnl),
                    "dca_better": pnl > lump_sum_pnl,
                },
                "monthly_details": monthly_details,
            },
            "summary": (
                f"DCA {monthly_amount / 1e6:,.1f}M/tháng x {months} tháng"
                f"{f' ({symbol.upper()})' if symbol else ''}. "
                f"Tổng {total_shares:,} CP, giá TB {avg_cost_price:,.2f}. "
                f"Giá trị hiện tại: {final_value / 1e6:,.1f}M. "
                f"**Lãi/Lỗ: {pnl / 1e6:,.1f}M ({pnl_pct:+.1f}%)**"
            ),
        }
