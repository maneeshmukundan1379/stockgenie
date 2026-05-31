"""
Stock assistant agent definitions.
"""

from typing import List, Optional

from agents import Agent, ModelSettings, function_tool
from pydantic import BaseModel

from llm_config import MODEL
from stock_tools import get_news, get_sector_tickers, get_stock_data, lookup_ticker


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
        "You are a stock analysis assistant. Using ONLY the provided technical "
        "indicators, fundamentals, and news, give a concise recommendation with "
        "clear reasoning. Use this structure:\n\n"
        "1) First line exactly: 'Recommendation: BUY', 'Recommendation: HOLD', or "
        "'Recommendation: SELL'.\n"
        "2) A section titled 'Parameters considered' — a compact bulleted list of the "
        "key signals with their actual values and a one-word read (bullish / bearish / "
        "neutral), e.g. 'RSI(14): 83 — bearish (overbought)'. Include the relevant "
        "technicals (trend/SMAs, MACD, RSI, momentum, volatility, position in range, "
        "volume, 30-day change) and fundamentals (P/E, PEG, growth, margin, dividend "
        "yield, beta, analyst target vs price, consensus), plus a one-line news read "
        "if present. Keep each bullet to one short line; do NOT explain what each "
        "metric means.\n"
        "3) A short 'What drove the decision' paragraph (2-4 sentences) naming the "
        "specific factors that mattered most, how they were weighed, and how any "
        "conflicting signals were resolved.\n\n"
        "Cite real numbers; do not invent data."
    ),
    model=MODEL,
)

sector_response_agent = Agent(
    name="SectorResponseAgent",
    instructions=(
        "You are a stock analysis assistant. You are given several stocks in a sector, "
        "each with full metrics: technicals (30-day change, trend, MACD, RSI, momentum, "
        "position in range, volatility) and fundamentals (P/E, PEG, growth, margin, "
        "analyst target vs price, consensus). Using ONLY this data, recommend what to "
        "BUY and what to SELL/AVOID. Group the stocks into 'BUY candidates' (strongest "
        "overall) and 'SELL/AVOID candidates' (weakest overall). For EACH stock give a "
        "one-line reason citing the specific metrics that placed it there, weighing "
        "BOTH technicals and fundamentals — not just 30-day change. Then add a "
        "'Bottom line' sentence summarizing the sector's overall trend and the relative "
        "strength that drove your picks. Be decisive and do not invent data."
    ),
    model=MODEL,
)

comparison_response_agent = Agent(
    name="StockComparisonAgent",
    instructions=(
        "You are a stock analysis assistant comparing several stocks the user owns or "
        "is considering. Using ONLY the provided per-stock metrics, directly answer the "
        "user's question (e.g., which ONE to sell, or which to buy).\n"
        "1) First line: state your pick clearly, e.g. 'Sell: TICKER' or 'Buy: TICKER'.\n"
        "2) A 'Ranking' list ordering ALL the stocks from strongest to weakest, each "
        "with a one-line reason citing key numbers (30-day change, trend, MACD, RSI, "
        "momentum, valuation, analyst target vs price).\n"
        "3) A short 'Why' paragraph explaining what made your pick the weakest (for a "
        "sell) or strongest (for a buy) relative to the others, weighing technicals and "
        "fundamentals and resolving conflicting signals.\n"
        "Be decisive; compare every stock provided; do not invent data."
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
