"""
Stock assistant data tools.
"""

import math
import os
import statistics
import time
from typing import Dict, List, Optional, Tuple

import requests
import yfinance as yf
from dotenv import load_dotenv
from yahooquery import Screener

load_dotenv(override=True)

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

DISCLAIMER = (
    "----------\n"
    "IMPORTANT DISCLAIMER: This response is automated, AI-generated output provided for "
    "general informational and educational purposes ONLY. It is NOT financial, investment, "
    "tax, accounting, or legal advice, No advisory, broker, or fiduciary relationship is "
    "created by your use of this tool. The creators and operators of this tool make no "
    "warranties of any kind and accept NO liability for any loss or damage arising from use "
    "of, or reliance on, this information."
)

CACHE_DURATION = 3600  # 1 hour
stock_cache: Dict[str, Tuple[dict, float]] = {}
news_cache: Dict[str, Tuple[dict, float]] = {}
entity_cache: Dict[str, Tuple[dict, float]] = {}
fundamentals_cache: Dict[str, Tuple[dict, float]] = {}

SECTOR_SCREENERS = {
    "technology": "ms_technology",
    "tech": "ms_technology",
    "finance": "ms_financial_services",
    "financial": "ms_financial_services",
    "healthcare": "ms_healthcare",
    "health": "ms_healthcare",
    "energy": "ms_energy",
    "retail": "ms_consumer_cyclical",
    "consumer": "ms_consumer_cyclical",
    "industrial": "ms_industrials",
    "basic_materials": "ms_basic_materials",
    "materials": "ms_basic_materials",
    "utilities": "ms_utilities",
    "real_estate": "ms_real_estate",
    "communication": "ms_communication_services",
    "consumer_defensive": "ms_consumer_defensive",
    "automotive": "ms_consumer_cyclical",
    "auto": "ms_consumer_cyclical",
}


def get_cached(cache_dict: Dict[str, Tuple[dict, float]], key: str) -> Optional[dict]:
    if key in cache_dict:
        data, timestamp = cache_dict[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
    return None


def set_cached(cache_dict: Dict[str, Tuple[dict, float]], key: str, data: dict) -> None:
    cache_dict[key] = (data, time.time())


def lookup_ticker(company_name: str) -> Optional[str]:
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        resp = requests.get(
            url,
            params={"q": company_name, "quotes_count": 1},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("quotes"):
            return data["quotes"][0]["symbol"]
    except Exception:
        return None
    return None


def get_sector_tickers(sector_name: str, max_stocks: int = 5) -> Optional[List[str]]:
    sector_key = sector_name.lower().strip()
    if sector_key not in SECTOR_SCREENERS:
        return None

    try:
        screener = Screener()
        screener_key = SECTOR_SCREENERS[sector_key]
        data = screener.get_screeners(screener_key, count=max_stocks)
        if screener_key in data and "quotes" in data[screener_key]:
            return [
                quote["symbol"]
                for quote in data[screener_key]["quotes"][:max_stocks]
            ]
    except Exception:
        return None
    return None


def get_30day_alpha(ticker: str) -> Optional[dict]:
    if not ALPHA_VANTAGE_API_KEY:
        return None

    key = f"{ticker}_30d"
    cached = get_cached(stock_cache, key)
    if cached:
        return cached

    try:
        resp = requests.get(
            ALPHA_VANTAGE_BASE_URL,
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "apikey": ALPHA_VANTAGE_API_KEY,
            },
            timeout=15,
        )
        data = resp.json()
        ts = data.get("Time Series (Daily)", {})
        if not ts:
            return None

        # Keep up to ~90 trading days (newest first) so EMA/MACD are reliable,
        # while the 30-day headline stats use only the most recent 30.
        daily = []
        for date in sorted(ts.keys(), reverse=True)[:90]:
            d = ts[date]
            daily.append(
                {
                    "date": date,
                    "open": float(d["1. open"]),
                    "high": float(d["2. high"]),
                    "low": float(d["3. low"]),
                    "close": float(d["4. close"]),
                    "volume": int(d["5. volume"]),
                }
            )

        recent = daily[:30]
        closes = [d["close"] for d in recent]
        highs = [d["high"] for d in recent]
        lows = [d["low"] for d in recent]

        result = {
            "ticker": ticker,
            "company_name": ticker,
            "daily_data": daily,
            "current_price": daily[0]["close"],
            "period_high": max(highs),
            "period_low": min(lows),
            "period_avg": sum(closes) / len(closes),
            "period_change_pct": ((closes[0] - closes[-1]) / closes[-1] * 100),
            "source": "Alpha Vantage API",
        }
        set_cached(stock_cache, key, result)
        return result
    except Exception:
        return None


def get_30day_yahoo(ticker: str) -> Optional[dict]:
    key = f"{ticker}_30d"
    cached = get_cached(stock_cache, key)
    if cached:
        return cached

    try:
        stock = yf.Ticker(ticker)
        # Fetch ~3 months so EMA/MACD are reliable; headline stats use last 30.
        hist = stock.history(period="3mo")
        if hist.empty:
            return None

        info = stock.info
        daily = []
        for date, row in hist.iterrows():
            daily.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
            )
        daily.reverse()  # newest first

        recent = daily[:30]
        closes = [d["close"] for d in recent]
        highs = [d["high"] for d in recent]
        lows = [d["low"] for d in recent]

        result = {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "daily_data": daily,
            "current_price": daily[0]["close"],
            "period_high": max(highs),
            "period_low": min(lows),
            "period_avg": sum(closes) / len(closes),
            "period_change_pct": ((closes[0] - closes[-1]) / closes[-1] * 100),
            "source": "Yahoo Finance API",
        }
        set_cached(stock_cache, key, result)
        return result
    except Exception:
        return None


def get_stock_data(ticker: str) -> Optional[dict]:
    data = get_30day_alpha(ticker)
    if data:
        return data
    return get_30day_yahoo(ticker)


def get_news(ticker: str) -> Optional[dict]:
    cached = get_cached(news_cache, ticker)
    if cached:
        return cached

    if ALPHA_VANTAGE_API_KEY:
        try:
            resp = requests.get(
                ALPHA_VANTAGE_BASE_URL,
                params={
                    "function": "NEWS_SENTIMENT",
                    "tickers": ticker,
                    "apikey": ALPHA_VANTAGE_API_KEY,
                    "limit": 10,
                },
                timeout=10,
            )
            data = resp.json()
            if "feed" in data:
                articles = [
                    {
                        "title": item.get("title", ""),
                        "source": item.get("source", ""),
                        "sentiment": item.get("overall_sentiment_label", "Neutral"),
                    }
                    for item in data["feed"][:5]
                ]
                result = {
                    "articles": articles,
                    "source": "Alpha Vantage News API",
                    "count": len(articles),
                }
                set_cached(news_cache, ticker, result)
                return result
        except Exception:
            pass

    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if news:
            articles = []
            for item in news[:5]:
                # yfinance's newer schema nests fields under "content".
                content = item.get("content", item)
                title = content.get("title") or item.get("title", "")
                provider = content.get("provider")
                if isinstance(provider, dict):
                    source = provider.get("displayName") or "Yahoo"
                else:
                    source = item.get("publisher", "Yahoo")
                if title:
                    articles.append({"title": title, "source": source})
            if articles:
                result = {
                    "articles": articles,
                    "source": "Yahoo Finance News",
                    "count": len(articles),
                }
                set_cached(news_cache, ticker, result)
                return result
    except Exception:
        return None
    return None


def get_fundamentals(ticker: str) -> Optional[dict]:
    """Fetch valuation, growth, profitability and analyst data from yfinance."""
    cached = get_cached(fundamentals_cache, ticker)
    if cached:
        return cached

    try:
        info = yf.Ticker(ticker).info
    except Exception:
        return None
    if not info:
        return None

    data = {
        "market_cap": info.get("marketCap"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("trailingPegRatio") or info.get("pegRatio"),
        "price_to_book": info.get("priceToBook"),
        "profit_margin": info.get("profitMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "target_mean_price": info.get("targetMeanPrice"),
        "target_high_price": info.get("targetHighPrice"),
        "target_low_price": info.get("targetLowPrice"),
        "recommendation": info.get("recommendationKey"),
        "num_analysts": info.get("numberOfAnalystOpinions"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
    }
    if not any(v is not None for v in data.values()):
        return None
    set_cached(fundamentals_cache, ticker, data)
    return data


def _human_money(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    for unit, threshold in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(value) >= threshold:
            return f"${value / threshold:.2f}{unit}"
    return f"${value:,.0f}"


def _fundamentals_text(fundamentals: Optional[dict], current_price: float) -> str:
    f = fundamentals
    if not f:
        return ""

    def num(value: Optional[float], suffix: str = "") -> str:
        return f"{value:.2f}{suffix}" if isinstance(value, (int, float)) else "n/a"

    def pct(value: Optional[float]) -> str:
        # profitMargins / revenueGrowth / earningsGrowth come back as fractions.
        if not isinstance(value, (int, float)):
            return "n/a"
        return f"{value * 100:+.1f}%"

    def div_yield(value: Optional[float]) -> str:
        # Current yfinance returns dividendYield already as a percent (e.g. 0.35);
        # older versions used a fraction (e.g. 0.0035). Normalize both.
        if not isinstance(value, (int, float)):
            return "n/a"
        v = value * 100 if value < 0.15 else value
        return f"{v:.2f}%"

    lines = ["Fundamentals & Analyst View:"]
    lines.append(f"- Market cap: {_human_money(f.get('market_cap'))}")
    lines.append(
        f"- P/E trailing / forward: {num(f.get('trailing_pe'))} / {num(f.get('forward_pe'))}"
    )
    lines.append(
        f"- PEG: {num(f.get('peg_ratio'))} | Price/Book: {num(f.get('price_to_book'))}"
    )
    lines.append(
        f"- Profit margin: {pct(f.get('profit_margin'))} | "
        f"Revenue growth: {pct(f.get('revenue_growth'))} | "
        f"Earnings growth: {pct(f.get('earnings_growth'))}"
    )
    lines.append(
        f"- Dividend yield: {div_yield(f.get('dividend_yield'))} | Beta: {num(f.get('beta'))}"
    )

    target = f.get("target_mean_price")
    if isinstance(target, (int, float)) and current_price:
        upside = (target - current_price) / current_price * 100
        lines.append(
            f"- Analyst mean target: ${target:.2f} ({upside:+.1f}% vs current); "
            f"range ${num(f.get('target_low_price'))}-${num(f.get('target_high_price'))}"
        )
    rec = f.get("recommendation")
    if rec:
        n = f.get("num_analysts")
        lines.append(
            f"- Analyst consensus: {rec}"
            + (f" ({n} analysts)" if n else "")
        )
    return "\n".join(lines) + "\n"


def _sma(values: List[float], n: int) -> Optional[float]:
    """Simple moving average of the last n chronological values."""
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def _ema_series(values: List[float], span: int) -> List[float]:
    """Exponential moving average series over chronological values."""
    if not values:
        return []
    k = 2.0 / (span + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _macd(values: List[float]) -> Optional[dict]:
    """MACD(12, 26, 9) over chronological closes."""
    if len(values) < 26:
        return None
    ema12 = _ema_series(values, 12)
    ema26 = _ema_series(values, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal = _ema_series(macd_line, 9)
    return {
        "macd": macd_line[-1],
        "signal": signal[-1],
        "histogram": macd_line[-1] - signal[-1],
    }


def _rsi(values: List[float], period: int = 14) -> Optional[float]:
    """Relative Strength Index over chronological closes."""
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_indicators(stock_data: dict) -> dict:
    """Compute a full set of technical indicators from 30-day daily data."""
    daily = stock_data.get("daily_data") or []
    if len(daily) < 4:
        return {}

    # daily_data is newest-first; build chronological (oldest -> newest) series.
    closes = [d["close"] for d in reversed(daily)]
    volumes = [d.get("volume", 0) for d in reversed(daily)]
    current = closes[-1]
    high = stock_data["period_high"]
    low = stock_data["period_low"]
    rng = high - low

    returns = [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1]
    ]
    volatility = (
        statistics.pstdev(returns) * math.sqrt(252) * 100 if len(returns) > 1 else None
    )

    def pct_change(periods: int) -> Optional[float]:
        if len(closes) > periods and closes[-(periods + 1)]:
            return (current - closes[-(periods + 1)]) / closes[-(periods + 1)] * 100
        return None

    # Max drawdown over the period.
    peak = closes[0]
    max_drawdown = 0.0
    for c in closes:
        peak = max(peak, c)
        if peak:
            max_drawdown = min(max_drawdown, (c - peak) / peak * 100)

    avg_volume = sum(volumes) / len(volumes) if volumes else 0
    recent_volume = sum(volumes[-5:]) / min(5, len(volumes)) if volumes else 0
    volume_trend = (
        (recent_volume - avg_volume) / avg_volume * 100 if avg_volume else 0.0
    )

    sma5, sma10, sma20 = _sma(closes, 5), _sma(closes, 10), _sma(closes, 20)
    if sma5 is not None and sma20 is not None:
        if sma5 > sma20 * 1.005:
            trend = "uptrend (SMA5 above SMA20)"
        elif sma5 < sma20 * 0.995:
            trend = "downtrend (SMA5 below SMA20)"
        else:
            trend = "flat / sideways (SMA5 ~ SMA20)"
    else:
        trend = "insufficient data"

    return {
        "current": current,
        "sma5": sma5,
        "sma10": sma10,
        "sma20": sma20,
        "rsi14": _rsi(closes, 14),
        "macd": _macd(closes),
        "momentum_5d": pct_change(5),
        "momentum_10d": pct_change(10),
        "volatility_annualized": volatility,
        "max_drawdown": max_drawdown,
        "position_in_range": (current - low) / rng * 100 if rng else 0.0,
        "avg_volume": avg_volume,
        "volume_trend": volume_trend,
        "trend": trend,
    }


def _indicators_text(stock_data: dict) -> str:
    ind = compute_indicators(stock_data)
    if not ind:
        return ""

    def fmt(value: Optional[float], suffix: str = "", money: bool = False) -> str:
        if value is None:
            return "n/a"
        return f"${value:.2f}" if money else f"{value:.2f}{suffix}"

    rsi = ind["rsi14"]
    if rsi is None:
        rsi_note = "n/a"
    elif rsi >= 70:
        rsi_note = f"{rsi:.0f} (overbought)"
    elif rsi <= 30:
        rsi_note = f"{rsi:.0f} (oversold)"
    else:
        rsi_note = f"{rsi:.0f} (neutral)"

    macd = ind["macd"]
    if macd is None:
        macd_note = "n/a (insufficient history)"
    else:
        bias = "bullish" if macd["histogram"] > 0 else "bearish"
        macd_note = (
            f"MACD {macd['macd']:.2f} vs signal {macd['signal']:.2f}, "
            f"histogram {macd['histogram']:+.2f} ({bias} crossover)"
        )

    return (
        "Technical Indicators:\n"
        f"- Trend: {ind['trend']}\n"
        f"- SMA 5 / 10 / 20: {fmt(ind['sma5'], money=True)} / "
        f"{fmt(ind['sma10'], money=True)} / {fmt(ind['sma20'], money=True)}\n"
        f"- MACD(12,26,9): {macd_note}\n"
        f"- RSI(14): {rsi_note}\n"
        f"- Momentum 5d / 10d: {fmt(ind['momentum_5d'], '%')} / "
        f"{fmt(ind['momentum_10d'], '%')}\n"
        f"- Annualized volatility: {fmt(ind['volatility_annualized'], '%')}\n"
        f"- Max drawdown: {fmt(ind['max_drawdown'], '%')}\n"
        f"- Position in 30-day range: {ind['position_in_range']:.0f}% "
        "(0%=at low, 100%=at high)\n"
        f"- Volume trend (recent vs avg): {ind['volume_trend']:+.0f}%\n"
    )


def summarize_stock_for_comparison(
    stock_data: dict, fundamentals: Optional[dict] = None
) -> str:
    """Compact one-stock summary used when comparing several stocks."""
    ind = compute_indicators(stock_data)
    ticker = stock_data["ticker"]
    name = stock_data.get("company_name", ticker)

    rsi = ind.get("rsi14")
    rsi_s = f"{rsi:.0f}" if isinstance(rsi, (int, float)) else "n/a"
    macd = ind.get("macd")
    macd_s = "n/a"
    if macd:
        macd_s = "bullish" if macd["histogram"] > 0 else "bearish"
    mom10 = ind.get("momentum_10d")
    mom10_s = f"{mom10:+.1f}%" if isinstance(mom10, (int, float)) else "n/a"
    vol = ind.get("volatility_annualized")
    vol_s = f"{vol:.0f}%" if isinstance(vol, (int, float)) else "n/a"

    line = (
        f"{ticker} ({name}):\n"
        f"  Technicals: 30-Day Change {stock_data['period_change_pct']:+.2f}% | "
        f"Trend {ind.get('trend', 'n/a')} | MACD {macd_s} | RSI(14) {rsi_s} | "
        f"Position in 30-day range {ind.get('position_in_range', 0):.0f}% | "
        f"Momentum 10d {mom10_s} | Volatility {vol_s}\n"
    )

    if fundamentals:
        f = fundamentals

        def n(v):
            return f"{v:.2f}" if isinstance(v, (int, float)) else "n/a"

        def gpct(v):
            return f"{v * 100:+.1f}%" if isinstance(v, (int, float)) else "n/a"

        target = f.get("target_mean_price")
        cur = stock_data["current_price"]
        if isinstance(target, (int, float)) and cur:
            upside = (target - cur) / cur * 100
            target_s = f"${target:.2f} ({upside:+.1f}%)"
        else:
            target_s = "n/a"
        line += (
            f"  Fundamentals: P/E fwd {n(f.get('forward_pe'))} | PEG {n(f.get('peg_ratio'))} | "
            f"Rev growth {gpct(f.get('revenue_growth'))} | Margin {gpct(f.get('profit_margin'))} | "
            f"Analyst target {target_s} | Consensus {f.get('recommendation') or 'n/a'}\n"
        )
    return line


def build_stock_context(
    stock_data: dict,
    news_data: Optional[dict],
    fundamentals: Optional[dict] = None,
) -> str:
    context = (
        f"Stock: {stock_data.get('company_name', stock_data['ticker'])} "
        f"({stock_data['ticker']})\n"
        f"Current: ${stock_data['current_price']:.2f}\n"
        f"30-Day High/Low: ${stock_data['period_high']:.2f} / "
        f"${stock_data['period_low']:.2f}\n"
        f"30-Day Average: ${stock_data['period_avg']:.2f}\n"
        f"30-Day Change: {stock_data['period_change_pct']:+.2f}%\n"
    )
    context += _indicators_text(stock_data)
    context += _fundamentals_text(fundamentals, stock_data["current_price"])
    if news_data:
        context += "Recent News:\n"
        for i, art in enumerate(news_data["articles"], 1):
            context += f"{i}. {art['title']}"
            if art.get("sentiment"):
                context += f" (Sentiment: {art['sentiment']})"
            context += "\n"
    return context
