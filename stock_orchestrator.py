"""
Stock assistant orchestration.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional

from agents import Agent, Runner
from pydantic import BaseModel

from llm_config import configure_llm
from stock_agents import (
    EntityExtraction,
    SectorDataPayload,
    StockDataPayload,
    comparison_response_agent,
    entity_extractor_agent,
    general_agent,
    sector_data_agent,
    sector_response_agent,
    stock_data_agent,
    stock_response_agent,
)
from stock_tools import (
    SECTOR_SCREENERS,
    build_stock_context,
    entity_cache,
    get_cached,
    get_fundamentals,
    get_news,
    get_sector_tickers,
    get_stock_data,
    lookup_ticker,
    set_cached,
    summarize_stock_for_comparison,
)


def _ensure_llm_ready() -> None:
    configure_llm()


def _strip_json_fence(content: str) -> str:
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    return content.strip()


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


async def _run_agent(agent: Agent, input_text: str) -> str:
    _ensure_llm_ready()
    result = await Runner.run(starting_agent=agent, input=input_text)
    return result.final_output.strip()


async def _run_agent_typed(agent: Agent, input_text: str, model_cls: type[BaseModel]) -> BaseModel:
    _ensure_llm_ready()
    result = await Runner.run(starting_agent=agent, input=input_text)
    return _coerce_output(result.final_output, model_cls)


async def extract_entities(question: str) -> Optional[dict]:
    cached = get_cached(entity_cache, question)
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
        set_cached(entity_cache, question, data)
        return data
    except Exception:
        return None


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


def _candidate_symbols(entities: dict) -> list:
    """Resolve the list of tickers referenced in a multi-stock question."""
    symbols = list(entities.get("tickers") or [])
    if not symbols:
        for company in entities.get("companies") or []:
            resolved = lookup_ticker(company)
            if resolved:
                symbols.append(resolved)
    # De-duplicate while preserving order.
    return list(dict.fromkeys(symbols))


async def answer_comparison(question: str, symbols: list, ts: str) -> Optional[str]:
    """Compare multiple stocks and answer which to buy/sell. Returns None to fall back."""
    stocks = []
    for sym in symbols[:8]:  # cap to keep latency reasonable
        data = get_stock_data(sym)
        if not data:
            continue
        fundamentals = get_fundamentals(sym)
        stocks.append(summarize_stock_for_comparison(data, fundamentals))
        time.sleep(0.3)

    if len(stocks) < 2:
        return None  # not enough data to compare; let caller use single-stock path

    context = "\n".join(stocks)
    prompt = (
        f"Stocks under consideration:\n\n{context}\n"
        f"Question: {question}\n\n"
        "Compare every stock above and answer the question, ranking them and "
        "justifying your pick with the data."
    )
    analysis = await _run_agent(comparison_response_agent, prompt)
    return (
        "Stock Comparison\n\n"
        f"{analysis}\n\n"
        "Sources: Alpha Vantage API, Yahoo Finance API, Google Gemini\n"
        f"Generated at {ts}"
    )


async def answer_question(question: str) -> str:
    """Public entrypoint: runs the analysis. The legal disclaimer is shown in the UI footer."""
    result = await _answer_question_core(question)
    if not result or not result.strip():
        return result
    return result.rstrip()


async def _answer_question_core(question: str) -> str:
    if not question.strip():
        return ""

    entities = await extract_entities(question)
    if not entities:
        return "Could not understand question."

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if entities["question_type"] == "stock_specific":
        # If the user named multiple stocks, compare them instead of analyzing one.
        symbols = _candidate_symbols(entities)
        if len(symbols) >= 2:
            comparison = await answer_comparison(question, symbols, ts)
            if comparison is not None:
                return comparison

        # Always consult news when we're doing analysis / making a recommendation.
        if entities.get("needs_analysis", True):
            entities["needs_news"] = True
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

        fundamentals = get_fundamentals(ticker)
        context = build_stock_context(stock_data, payload.news_data, fundamentals)
        analysis = await _run_agent(
            stock_response_agent,
            f"{context}\nQuestion: {question}\n\n"
            "List the parameters considered and explain what drove the recommendation, "
            "citing the data above.",
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
            fundamentals = get_fundamentals(s["ticker"])
            stock_list += "\n" + summarize_stock_for_comparison(s, fundamentals)
            time.sleep(0.3)

        sector_prompt = (
            f"Sector: {payload.sector.title()}\n\nStocks and their metrics:\n{stock_list}\n"
            f"Question: {question}\n\n"
            "Answer the exact question, weighing each stock's technicals and "
            "fundamentals (not only 30-day change). If asking for decliners, focus on "
            "the weakest; if asking for top performers, focus on the strongest."
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
