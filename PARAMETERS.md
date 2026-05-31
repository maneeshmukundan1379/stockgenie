# What the Stock Assistant Looks At (Plain-English Guide)

This guide explains, in everyday language, everything the assistant considers when
it answers you and how it makes its decision — no finance background needed.

Think of the assistant like a careful friend who, before giving an opinion on a stock,
checks three things:

1. What has the price been doing lately? (the "technicals")
2. Is the company healthy and fairly priced? (the "fundamentals")
3. What's the latest news?

It then weighs all of that and gives you a clear takeaway.

---

## How it understands your question

The first thing it does is figure out what you're really asking:

- About one company? (e.g. "Should I buy Apple?") → it does a full check on that
  one stock.
- Comparing several? (e.g. "Which should I sell — Apple, Tesla, or Nvidia?") →
  it ranks them against each other.
- About a whole sector? (e.g. "What's worth buying in technology?") → it looks at
  the top companies in that sector and sorts the stronger ones from the weaker ones.
- A general money question? (e.g. "What is a P/E ratio?") → it just explains the
  concept; no live data needed.

It also notices whether you want advice ("should I buy/sell?") or just a fact
("what's the price?"). If you want advice, it does the deeper analysis and also pulls
in recent news. If you only want a fact, it gives you the number without a lot of
commentary.

Where the information comes from: live stock prices, company financials, and recent
news from trusted market data providers, with the actual reasoning done by an AI model.
Results are briefly remembered (about an hour) so repeated questions are fast.

---

## Everything it looks at, in plain English

### Price basics

- Current price — what one share costs right now, like today's sticker price.
- 30-day high / low — the most expensive and the cheapest the share got in the
  last month.
- 30-day average — the "typical" price over the last month.
- 30-day change — whether the price is up or down compared to a month ago, as a
  percentage. +8% means it's 8% higher than a month back.

### "What has the price been doing?" (technicals)

- Moving average — the average price over the last several days. It smooths out
  daily noise so you can see the real direction — like averaging your last few test
  scores instead of panicking over one bad day.
- Trend — it compares a recent average (last 5 days) with a longer one (last 20
  days). If the recent one is higher, the stock is generally rising; if lower,
  falling; if about the same, flat/sideways.
- "Overbought / oversold" meter (RSI) — a 0-to-100 score for whether a stock has
  been bought or sold too aggressively. Above 70 = it climbed so fast it may be due
  for a breather (overbought); below 30 = it dropped so hard it may be due for a
  bounce (oversold); in between is normal.
- Momentum gauge (MACD) — tells whether upward energy is building (a positive,
  bullish sign) or fading (a negative, bearish sign).
- Recent momentum — simply how much the price moved over the last week or two.
  Positive means it's been climbing.
- Volatility — how bumpy the ride is. High volatility means big up-and-down swings
  (more stress and risk); low means a smoother ride.
- Worst drop (max drawdown) — the biggest fall from a recent high. It answers:
  "if I'd bought at the worst moment, how far down would I have been?"
- Position in the month's range — where today's price sits between the month's
  lowest (0%) and highest (100%). 90% means it's near its monthly peak.
- Trading activity (volume) — how many shares change hands on a typical day (how
  busy/popular the stock is), and whether that activity is picking up or quieting
  down lately.

### "Is the company healthy and fairly priced?" (fundamentals)

- Company size (market cap) — the company's overall price tag. Bigger usually means
  more established.
- P/E ratio — how many dollars you pay for each dollar of the company's profit. A
  high number means investors are paying a premium (often betting on growth); a low one
  can mean a bargain — or trouble. It comes in two flavors: based on past profit and
  on expected future profit.
- Price-vs-growth (PEG) — the P/E adjusted for how fast the company is growing. It
  helps judge whether a high price is justified by fast growth.
- Price-to-book — the share price compared to the company's accounting net worth.
- Profit margin — out of every $1 of sales, how much is actual profit. Higher is
  healthier.
- Revenue growth — is the company selling more than a year ago?
- Earnings (profit) growth — is its profit growing compared to a year ago?
- Dividend yield — if the company pays cash to its shareholders, this is that payout
  as a percentage of the share price (a bit like interest on savings).
- Jumpiness vs the market (beta) — how wild the stock is compared to the market
  overall. 1.0 = moves with the market; above 1 = swings more; below 1 = calmer.
- Analysts' price target — professional analysts' average guess of a "fair" price,
  and how far that sits above or below today's price (the potential upside).
- Analysts' overall vote — their combined recommendation: buy, hold, or sell (and
  how many analysts weighed in).
- 52-week high / low — the highest and lowest price over the past year, for
  longer-term context.

### "What's the latest news?"

- Recent headlines — up to five recent stories about the company.
- News mood (sentiment) — whether that news skews positive, negative, or neutral.

---

## How it decides

The assistant doesn't just look at one number — it weighs all of the above together,
the way a thoughtful person would, and explains its reasoning. In particular it looks
at:

- Direction & energy: is the price trending up, and is momentum building?
- Is it stretched? has it run up so far it's "overbought," or is it near the top of
  its recent range?
- Risk: how bumpy and how deep have the recent drops been?
- Value & quality: is the company fairly priced, profitable, and growing?
- The pros' view: do analysts see room to rise, and what's their overall vote?
- The buzz: is recent news helping or hurting?

When signals disagree — say, strong momentum but an "overbought" warning, or a cheap
price but weak growth — it explains how it balanced them to reach a final
Buy / Hold / Sell takeaway (or, when comparing stocks, a ranking from strongest to
weakest).

Every answer also names the data sources used and the time it was generated.

---

## A worked example (start to finish)

You ask: "Based on the last month, should I buy or sell Apple?"

Step 1 — It understands the question. This is about one company (Apple), you want
advice, so it does a full check and pulls in recent news.

Step 2 — It gathers the data. It looks up Apple, downloads the last month of prices,
works out all the "what's the price been doing" measures, fetches the company's
financial health figures, and grabs recent headlines.

Step 3 — It lays out the numbers. (Example values, for illustration)

| What it looked at | Example | What that means |
| --- | --- | --- |
| 30-day change | +6.5% | Up over the month |
| Trend | rising | Recent prices above the longer average |
| Overbought/oversold (RSI) | 78 | Overbought — ran up fast, may need a breather |
| Momentum (MACD) | building up | Upward energy still positive |
| Position in month's range | 94% | Trading near its monthly high |
| Volatility | low-ish | Fairly calm ride |
| P/E (future) | 29 | On the pricey side |
| Sales / profit growth | +8% / +11% | Growing steadily |
| Analysts' target | +4% above today | Pros see only a little room left |
| News mood | mostly positive | Recent buzz is good |

Step 4 — It weighs it all. The trend, momentum, and news are positive — but the
stock looks overbought, is near the top of its monthly range, is priced richly, and
analysts see only ~4% more room. In other words, a lot of the good news already seems
baked into the price.

Step 5 — The answer you'd see (illustrative):

```
Apple (AAPL) - Analysis

Recommendation: HOLD

Parameters considered:
- 30-day change: +6.5% — positive
- Trend: rising — positive
- Overbought/oversold: 78 — caution (overbought)
- Momentum: building — positive
- Position in month's range: 94% — caution (near the top)
- Volatility: low-ish — neutral
- Price vs profit (P/E): 29 — slightly expensive
- Sales / profit growth: +8% / +11% — positive
- Analysts' target: +4% above today — limited room
- News mood: mostly positive — mildly positive

What drove the decision: The trend, momentum, and news are clearly positive,
but the stock looks overbought, is sitting near the top of its monthly range,
is priced on the expensive side, and analysts see only about 4% more upside.
Steady growth and good news support holding it, but the limited room to climb
argues against chasing it right now — so HOLD rather than BUY.

Stats: $213.40 | 30-Day: +6.50%
Generated at 2026-05-31 09:51:00
```

Note: the numbers above are made up to show the idea — a real answer uses live data.

---

## Important to know

- The assistant only uses the real data it pulled in; it's instructed not to make up
  numbers.
- All the price math is done by the program, so the figures are consistent; the AI
  handles the explanation and the judgment.
- This is educational information only — not financial advice. Markets carry risk,
  past performance doesn't guarantee future results, and you should do your own research
  and consult a licensed advisor before investing. The full disclaimer is always shown
  at the bottom of the app.
