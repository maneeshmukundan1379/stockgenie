# 📈 Stock Assistant - Complete Flow Diagram

## 📊 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Stock Assistant                          │
│                                                              │
│  CLI Input → Entity Extraction → Data Fetch → AI Response   │
│                   → Formatted Output                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Runtime Flow

### Flow: Running `stock_assistant_agent.py`

```
Run: python stock_assistant_agent.py "question"
        ↓
┌───────────────────────────────┐
│ main()                        │
│ file: stock_assistant_agent.py│
│ - Read CLI args               │
│ - Build question string       │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ answer_question_sync()        │
│ file: stock_orchestrator.py   │
│ - Run async orchestration     │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ answer_question()             │
│ file: stock_orchestrator.py   │
│ - Validate input              │
│ - Route by question_type      │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ extract_entities()            │
│ file: stock_orchestrator.py   │
│ - Check entity_cache          │
│ - Call StockEntityExtractor   │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ Decision: question_type?      │
│ 1) stock_specific             │
│ 2) sector                     │
│ 3) general                    │
└───────────────┬───────────────┘
         ┌──────┼───────────┐
         ↓      ↓           ↓
```

---

## 🧠 Agent Execution Flow

### 1) Stock-Specific Flow

```
┌───────────────────────────────┐
│ fetch_stock_payload()         │
│ file: stock_orchestrator.py   │
│ - Call StockDataAgent         │
│ - Fallback to direct tools    │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ StockDataAgent                │
│ file: stock_agents.py         │
│ Tools: lookup_ticker          │
│        get_stock_data         │
│        get_news               │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ Decision: needs_analysis?     │
│  - No → format simple stats   │
│  - Yes → build context        │
└───────────────┬───────────────┘
         ┌──────┴───────────┐
         ↓                  ↓
┌──────────────────────┐   ┌───────────────────────────────┐
│ Return simple stats  │   │ build_stock_context()          │
│ file: stock_orchestrator.py   │
│ + source + timestamp │   └───────────────┬───────────────┘
└──────────────┬───────┘                   ↓
               │              ┌───────────────────────────────┐
               │              │ StockResponseAgent            │
               │              │ file: stock_agents.py         │
               │              │ - Use context for analysis    │
               │              └───────────────┬───────────────┘
               │                              ↓
               └──────────────→ Final response
```

### 2) Sector Flow

```
┌───────────────────────────────┐
│ fetch_sector_payload()        │
│ file: stock_orchestrator.py   │
│ - Call SectorDataAgent        │
│ - Fallback to direct tools    │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ SectorDataAgent               │
│ file: stock_agents.py         │
│ Tools: get_sector_tickers     │
│        get_stock_data         │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│ SectorResponseAgent           │
│ file: stock_agents.py         │
│ - Answer based on performance │
└───────────────┬───────────────┘
                ↓
        Final response
```

### 3) General Flow

```
┌───────────────────────────────┐
│ StockGeneralAgent             │
│ file: stock_agents.py         │
│ - Answer general question     │
└───────────────┬───────────────┘
                ↓
        Final response
```

---

## 🧩 Key Components

```
Agents (stock_agents.py)
├─ StockEntityExtractor
├─ StockDataAgent
├─ StockResponseAgent
├─ SectorDataAgent
├─ SectorResponseAgent
└─ StockGeneralAgent

Tools (stock_tools.py)
├─ lookup_ticker
├─ get_stock_data
├─ get_news
└─ get_sector_tickers

Orchestration (stock_orchestrator.py)
├─ extract_entities
├─ fetch_stock_payload
├─ fetch_sector_payload
└─ answer_question
```
