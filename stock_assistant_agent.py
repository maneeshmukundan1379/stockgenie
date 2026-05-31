"""
Stock Assistant (Agent-based)

CLI entrypoint for the modular stock assistant.
"""

from stock_orchestrator import answer_question_sync


def main() -> None:
    import sys

    if len(sys.argv) < 2:
        print('Usage: python stock_assistant_agent.py "Your question"')
        return
    question = " ".join(sys.argv[1:])
    print(answer_question_sync(question))


if __name__ == "__main__":
    main()
"""
Stock Assistant (Agent-based)

Core features:
- NLP extraction for companies/tickers/sectors
- 30-day historical data (Alpha Vantage -> Yahoo Finance fallback)
- News integration for predictive questions
- Sector analysis
- Simple answers for simple questions, deeper analysis when needed
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
import yfinance as yf
from agents import Agent, ModelSettings, Runner, function_tool
from dotenv import load_dotenv
from pydantic import BaseModel
from yahooquery import Screener

from llm_config import MODEL, configure_llm

load_dotenv(override=True)

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

CACHE_DURATION = 3600  # 1 hour
stock_cache: Dict[str, Tuple[dict, float]] = {}
news_cache: Dict[str, Tuple[dict, float]] = {}
entity_cache: Dict[str, Tuple[dict, float]] = {}

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


def _get_cached(cache_dict: Dict[str, Tuple[dict, float]], key: str) -> Optional[dict]:
    if key in cache_dict:
        data, timestamp = cache_dict[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
    return None


def _set_cached(cache_dict: Dict[str, Tuple[dict, float]], key: str, data: dict) -> None:
    cache_dict[key] = (data, time.time())


def _ensure_openai_key() -> None:
    configure_llm()


class EntityExtraction(BaseModel):
    companies: List[str] = []
    tickers: List[str] = []
    sectors: List[str] = []
    question_type: str = "general"
    main_entity: str = ""
    needs_analysis: bool = True
    needs_news: bool = False


class StockDataPayload(BaseModel):
    ok: bool
    error: Optional[str] = None
    ticker: Optional[str] = None
    stock_data: Optional[dict] = None
    news_data: Optional[dict] = None


class SectorDataPayload(BaseModel):
    ok: bool
    error: Optional[str] = None
    sector: Optional[str] = None
    stocks: List[dict] = []


def _coerce_output(result: object, model_cls: type[BaseModel]) -> BaseModel:
    if isinstance(result, model_cls):
        return result
    if isinstance(result, BaseModel):
        return model_cls(**result.model_dump())
    if isinstance(result, dict):
        return model_cls(**result)
    if isinstance(result, str):
        return model_cls(**json.loads(_strip_json_fence(result)))
    raise ValueError("Unexpected agent output type")


@function_tool
def lookup_ticker_tool(company_name: str) -> Optional[str]:
    """Return ticker for a company name."""
    return lookup_ticker(company_name)


@function_tool
def get_stock_data_tool(ticker: str) -> Optional[dict]:
    """Return 30-day stock data for a ticker."""
    return get_stock_data(ticker)


@function_tool
def get_news_tool(ticker: str) -> Optional[dict]:
    """Return recent news for a ticker."""
    return get_news(ticker)


@function_tool
def get_sector_tickers_tool(sector_name: str, max_stocks: int = 5) -> Optional[List[str]]:
    """Return tickers for a sector."""
    return get_sector_tickers(sector_name, max_stocks=max_stocks)


ENTITY_INSTRUCTIONS = (
    "Extract stock market entities from the question. "
    "Return JSON with keys: companies, tickers, sectors, question_type, main_entity, "
    "needs_analysis, needs_news. Use question_type = stock_specific, sector, or general. "
    "If the user asks for advice or a recommendation (buy, sell, hold, invest, "
    "should I, worth it, good buy, etc.), set needs_analysis=true and needs_news=true. "
    "Do not include generic words like 'stocks' or 'companies' as company names. "
    "Output JSON only, no extra text."
)

entity_extractor_agent = Agent(
    name="StockEntityExtractor",
    instructions=ENTITY_INSTRUCTIONS,
    model=MODEL,
    output_type=EntityExtraction,
)

stock_response_agent = Agent(
    name="StockResponseAgent",
    instructions=(
        "You are a stock analysis assistant. Using ONLY the provided 30-day price "
        "data, trend metrics, and any news, give a clear recommendation. "
        "Start your answer with one of: 'Recommendation: BUY', "
        "'Recommendation: HOLD', or 'Recommendation: SELL'. "
        "Then give 2-4 short bullet points justifying it, each citing specific "
        "numbers from the data. Be decisive but do not invent data. "
        "End with exactly this line: "
        "'Educational analysis based on 1-month trends, not professional financial advice.'"
    ),
    model=MODEL,
)

sector_response_agent = Agent(
    name="SectorResponseAgent",
    instructions=(
        "You are a stock analysis assistant. Using ONLY the provided sector "
        "performance data (each stock's 30-day change), recommend what to BUY and "
        "what to SELL/AVOID, citing each stock's 30-day change %. Be decisive and do "
        "not invent data. End with exactly this line: "
        "'Educational analysis based on 1-month trends, not professional financial advice.'"
    ),
    model=MODEL,
)

general_agent = Agent(
    name="StockGeneralAgent",
    instructions=(
        "Answer general stock market questions succinctly. "
        "If you are unsure, say so and avoid speculation."
    ),
    model=MODEL,
)

stock_data_agent = Agent(
    name="StockDataAgent",
    instructions=(
        "You are a data fetch agent. Given a JSON payload with keys: "
        "ticker, company, needs_news. Use tools to resolve missing ticker, "
        "fetch stock data, and fetch news when requested. Return JSON with "
        "keys: ok, error, ticker, stock_data, news_data."
    ),
    tools=[lookup_ticker_tool, get_stock_data_tool, get_news_tool],
    model=MODEL,
    model_settings=ModelSettings(tool_choice="required"),
    output_type=StockDataPayload,
)

sector_data_agent = Agent(
    name="SectorDataAgent",
    instructions=(
        "You are a data fetch agent. Given a JSON payload with keys: sector, max_stocks. "
        "Use tools to fetch sector tickers and then stock data for each ticker. "
        "Return JSON with keys: ok, error, sector, stocks."
    ),
    tools=[get_sector_tickers_tool, get_stock_data_tool],
    model=MODEL,
    model_settings=ModelSettings(tool_choice="required"),
    output_type=SectorDataPayload,
)


def _strip_json_fence(content: str) -> str:
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    return content.strip()


async def _run_agent(agent: Agent, input_text: str) -> str:
    _ensure_openai_key()
    result = await Runner.run(starting_agent=agent, input=input_text)
    return result.final_output.strip()


async def _run_agent_typed(agent: Agent, input_text: str, model_cls: type[BaseModel]) -> BaseModel:
    _ensure_openai_key()
    result = await Runner.run(starting_agent=agent, input=input_text)
    return _coerce_output(result.final_output, model_cls)


async def extract_entities(question: str) -> Optional[dict]:
    cached = _get_cached(entity_cache, question)
    if cached:
        return cached

    prompt = (
        f'Question: "{question}"\n\n'
        "Return JSON with:\n"
        "- companies: list of company names\n"
        "- tickers: list of stock tickers\n"
        "- sectors: list of sectors\n"
        '- question_type: "stock_specific", "sector", or "general"\n'
        "- main_entity: primary entity\n"
        "- needs_analysis: true/false\n"
        "- needs_news: true/false\n"
    )

    try:
        output = await _run_agent_typed(entity_extractor_agent, prompt, EntityExtraction)
        data = output.model_dump()
        _set_cached(entity_cache, question, data)
        return data
    except Exception:
        return None


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
    cached = _get_cached(stock_cache, key)
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

        daily = []
        for date in sorted(ts.keys(), reverse=True)[:30]:
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

        closes = [d["close"] for d in daily]
        highs = [d["high"] for d in daily]
        lows = [d["low"] for d in daily]

        result = {
            "ticker": ticker,
            "company_name": ticker,
            "daily_data": daily,
            "current_price": closes[0],
            "period_high": max(highs),
            "period_low": min(lows),
            "period_avg": sum(closes) / len(closes),
            "period_change_pct": ((closes[0] - closes[-1]) / closes[-1] * 100),
            "source": "Alpha Vantage API",
        }
        _set_cached(stock_cache, key, result)
        return result
    except Exception:
        return None


def get_30day_yahoo(ticker: str) -> Optional[dict]:
    key = f"{ticker}_30d"
    cached = _get_cached(stock_cache, key)
    if cached:
        return cached

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
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
        daily.reverse()

        closes = [d["close"] for d in daily]
        highs = [d["high"] for d in daily]
        lows = [d["low"] for d in daily]

        result = {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "daily_data": daily,
            "current_price": closes[0],
            "period_high": max(highs),
            "period_low": min(lows),
            "period_avg": sum(closes) / len(closes),
            "period_change_pct": ((closes[0] - closes[-1]) / closes[-1] * 100),
            "source": "Yahoo Finance API",
        }
        _set_cached(stock_cache, key, result)
        return result
    except Exception:
        return None


def get_stock_data(ticker: str) -> Optional[dict]:
    data = get_30day_alpha(ticker)
    if data:
        return data
    return get_30day_yahoo(ticker)


def get_news(ticker: str) -> Optional[dict]:
    cached = _get_cached(news_cache, ticker)
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
                _set_cached(news_cache, ticker, result)
                return result
        except Exception:
            pass

    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if news:
            articles = [
                {"title": item.get("title", ""), "source": item.get("publisher", "Yahoo")}
                for item in news[:5]
            ]
            result = {
                "articles": articles,
                "source": "Yahoo Finance News",
                "count": len(articles),
            }
            _set_cached(news_cache, ticker, result)
            return result
    except Exception:
        return None
    return None


def _build_stock_context(stock_data: dict, news_data: Optional[dict]) -> str:
    context = (
        f"Stock: {stock_data.get('company_name', stock_data['ticker'])} "
        f"({stock_data['ticker']})\n"
        f"Current: ${stock_data['current_price']:.2f}\n"
        f"30-Day High/Low: ${stock_data['period_high']:.2f} / "
        f"${stock_data['period_low']:.2f}\n"
        f"30-Day Change: {stock_data['period_change_pct']:+.2f}%\n"
    )
    if news_data:
        context += "Recent News:\n"
        for i, art in enumerate(news_data["articles"], 1):
            context += f"{i}. {art['title']}"
            if art.get("sentiment"):
                context += f" (Sentiment: {art['sentiment']})"
            context += "\n"
    return context


async def fetch_stock_payload(entities: dict) -> StockDataPayload:
    ticker = entities["tickers"][0] if entities.get("tickers") else None
    company = entities["companies"][0] if entities.get("companies") else None
    input_payload = json.dumps(
        {
            "ticker": ticker,
            "company": company,
            "needs_news": bool(entities.get("needs_news")),
        }
    )
    try:
        return await _run_agent_typed(stock_data_agent, input_payload, StockDataPayload)
    except Exception:
        pass

    resolved_ticker = ticker
    if not resolved_ticker and company:
        resolved_ticker = lookup_ticker(company)
    if not resolved_ticker:
        return StockDataPayload(ok=False, error="Could not resolve ticker.")

    stock_data = get_stock_data(resolved_ticker)
    if not stock_data:
        return StockDataPayload(ok=False, error="Could not retrieve stock data.")

    news_data = get_news(resolved_ticker) if entities.get("needs_news") else None
    return StockDataPayload(
        ok=True,
        ticker=resolved_ticker,
        stock_data=stock_data,
        news_data=news_data,
    )


async def fetch_sector_payload(entities: dict, max_stocks: int = 5) -> SectorDataPayload:
    sector = (
        entities["sectors"][0]
        if entities.get("sectors")
        else entities.get("main_entity")
    )
    input_payload = json.dumps({"sector": sector, "max_stocks": max_stocks})
    try:
        return await _run_agent_typed(sector_data_agent, input_payload, SectorDataPayload)
    except Exception:
        pass

    tickers = get_sector_tickers(sector, max_stocks=max_stocks)
    if not tickers:
        return SectorDataPayload(ok=False, error="Sector not found.", sector=sector)

    stocks = []
    for t in tickers:
        d = get_stock_data(t)
        if d:
            stocks.append(d)
            time.sleep(0.5)
    if not stocks:
        return SectorDataPayload(ok=False, error="No sector data.", sector=sector)
    return SectorDataPayload(ok=True, sector=sector, stocks=stocks)


async def answer_question(question: str) -> str:
    if not question.strip():
        return ""

    entities = await extract_entities(question)
    if not entities:
        return "Could not understand question."

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if entities["question_type"] == "stock_specific":
        payload = await fetch_stock_payload(entities)
        if not payload.ok:
            return payload.error or "Could not retrieve stock data."
        if not payload.stock_data or not payload.ticker:
            return "Could not retrieve stock data."

        stock_data = payload.stock_data
        ticker = payload.ticker
        company = stock_data.get("company_name", ticker)

        if not entities.get("needs_analysis", True):
            return (
                f"{company} ({ticker})\n\n"
                f"Current Price: ${stock_data['current_price']:.2f}\n"
                f"30-Day High: ${stock_data['period_high']:.2f}\n"
                f"30-Day Low: ${stock_data['period_low']:.2f}\n"
                f"30-Day Change: {stock_data['period_change_pct']:+.2f}%\n\n"
                f"Source: {stock_data['source']}\n"
                f"Retrieved at {ts}"
            )

        context = _build_stock_context(stock_data, payload.news_data)
        analysis = await _run_agent(
            stock_response_agent,
            f"{context}\nQuestion: {question}\n\nProvide analysis citing the data.",
        )
        response = (
            f"{company} ({ticker}) - Analysis\n\n"
            f"{analysis}\n\n"
            f"Stats: ${stock_data['current_price']:.2f} | "
            f"30-Day: {stock_data['period_change_pct']:+.2f}%\n"
            f"Sources: {stock_data['source']}"
        )
        if payload.news_data:
            response += f", {payload.news_data['source']}"
        response += f", Google Gemini\nGenerated at {ts}"
        return response

    if entities["question_type"] == "sector":
        payload = await fetch_sector_payload(entities, max_stocks=5)
        if not payload.ok:
            if payload.error == "Sector not found.":
                available = ", ".join(sorted(set(SECTOR_SCREENERS.keys())))
                return (
                    f"Sector '{payload.sector}' not found. "
                    f"Available sectors: {available}"
                )
            return payload.error or "Could not retrieve sector data."
        if not payload.stocks or not payload.sector:
            return "Could not retrieve sector data."

        stock_list = ""
        for s in sorted(
            payload.stocks, key=lambda x: x["period_change_pct"], reverse=True
        ):
            stock_list += (
                f"\n- {s['ticker']} ({s.get('company_name', s['ticker'])}): "
                f"{s['period_change_pct']:+.2f}%"
            )

        sector_prompt = (
            f"Sector: {payload.sector.title()}\nStocks:{stock_list}\n\n"
            f"Question: {question}\n\n"
            "Answer the exact question. If asking for declining stocks, list those "
            "with negative/lowest performance. If asking for top performers, list "
            "highest gains."
        )

        analysis = await _run_agent(sector_response_agent, sector_prompt)
        return (
            f"{payload.sector.title()} Sector\n\n"
            f"{analysis}\n\n"
            "Sources: Alpha Vantage API, Yahoo Finance API, Google Gemini\n"
            f"Generated at {ts}"
        )

    answer = await _run_agent(
        general_agent, f"Answer this stock market question: {question}"
    )
    return f"{answer}\n\nSource: Google Gemini\nGenerated at {ts}"


def answer_question_sync(question: str) -> str:
    return asyncio.run(answer_question(question))


def main() -> None:
    import sys

    if len(sys.argv) < 2:
        print("Usage: python stock_assistant_agent.py \"Your question\"")
        return
    question = " ".join(sys.argv[1:])
    print(answer_question_sync(question))


if __name__ == "__main__":
    main()
