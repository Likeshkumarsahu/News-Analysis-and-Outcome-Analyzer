# 📰 Newsana AI — News Analysis & Outcome Analyzer

A real-time, Retrieval-Augmented Generation (RAG) based news analysis and outcome forecasting system. It collects live news from multiple global RSS feeds plus historical coverage from GDELT and NewsAPI, indexes documents in ChromaDB, builds entity Knowledge Graphs, performs hybrid search (BM25 + Semantic + CrossEncoder Reranking), classifies sentiment via RoBERTa, predicts event impact using Machine Learning (TF-IDF + Logistic Regression with rule-based fallback), explains decisions using Explainable AI (LIME), orchestrates multi-agent tasks via a LangGraph-based agent crew, accelerates responses with Redis caching, and generates natural language insights through a local LLM (Ollama) or your choice of cloud provider (Groq, Anthropic Claude, OpenAI, or Google Gemini).

> **6th Semester Engineering Project**
> AI/ML Pipeline • RAG • Knowledge Graph • Multi-Agent Analysis • XAI • Multi-Provider LLM • Redis • Flask Dashboard

---

## 🔍 Overview

Newsana AI provides an end-to-end intelligence framework designed to digest raw, fast-moving news streams and transform them into structured, actionable, and explainable insights.

### Key Capabilities

* **Live + Historical Multi-Source Ingestion:** Real-time RSS across 9 major global & regional feeds (BBC, Al Jazeera, Reuters, The Hindu, NDTV, India Today, Times of India, Hindustan Times, Economic Times), plus historical backfill from the **GDELT DOC 2.0 API** and **NewsAPI**, fetched concurrently with `httpx` + `tenacity` retry-on-429/5xx and cached in Redis.
* **Smart Deduplication & Preprocessing:** MD5-hash deduplication across all sources (RSS, GDELT, NewsAPI) prevents storing duplicate articles, followed by SpaCy NLP text cleaning and Named Entity Recognition (NER).
* **Persistent Vector & Graph Indexing:** Chunks articles into ChromaDB vector storage (`all-MiniLM-L6-v2`) and extracts entity co-occurrence Knowledge Graphs using NetworkX.
* **Hybrid Search Engine:** Combines sparse BM25 keyword matching with dense semantic vector search, followed by a CrossEncoder reranker (`ms-marco-MiniLM-L-6-v2`) for optimal precision.
* **RoBERTa Sentiment Analysis:** Micro-fine-grained sentiment classification (POSITIVE, NEGATIVE, NEUTRAL) with confidence scores using Cardiff NLP's RoBERTa.
* **Machine Learning Impact Classifier:** Predicts event impact severity (HIGH, MEDIUM, LOW) using a trained TF-IDF + Logistic Regression model with automatic rule-based signal fallback.
* **Explainable AI (LIME XAI):** Computes word-level feature importance for sentiment and impact predictions to eliminate black-box AI opacity.
* **Multi-Agent Architecture:** Sequential LangGraph pipeline of 3 autonomous agents (Senior News Analyst, Strategic Intelligence Analyst, Editorial Fact Checker) for deep research dossiers — runs on whichever LLM provider/model you have selected.
* **Multi-Provider LLM Explainer:** Choose per-query between local CPU-friendly generation via Ollama (`llama3.2:3b`), or bring your own key for Groq, Anthropic Claude, OpenAI, or Google Gemini — with automatic provider fallback if your first choice is unavailable.
* **Redis Caching:** Two independent caching layers — query-level LLM analysis caching, and raw API-response caching for the historical ingestion connectors — both degrade gracefully if Redis is unreachable.
* **Interactive Modern Web Dashboard:** Flask-backed interface with dynamic gauges, a D3.js Knowledge Graph visualization, live provider picker, and real-time controls.
* **Automated RAG Evaluation:** Built-in quantitative metric calculator measuring Context Precision, Context Recall, Answer Relevancy, and Faithfulness.

---

# 🏗️ System Architecture

```text
     ┌───────────────────────────┐   ┌──────────────────────────────────────┐
     │  RSS Feeds (9 sources)    │   │  GDELT DOC 2.0 + NewsAPI (historical) │
     └─────────────┬─────────────┘   └────────────────────┬───────────────────┘
                   │                                      │ async, httpx + tenacity retry
                   │                                      │ Redis-cached (cache/api_cache.py)
                   ▼                                      ▼
              [Ingestion Engine]  feedparser + connectors, MD5 dedup across all sources
                                           │
                                           ▼
                        [NLP Preprocessing] SpaCy (en_core_web_sm)
                                Entity Extraction & Cleaning
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                     ▼
            [Vector Database] ChromaDB               [Knowledge Graph]
            embeddings: all-MiniLM-L6-v2             Entity Co-occurrence (JSON/NetworkX)
                        └──────────────────┬──────────────────┘
                                           │
                                           ▼
                              [Hybrid Search Engine]
                              BM25 Keyword Search (Top 20)
                            + Semantic Vector Search (Top 20)
                            + CrossEncoder Reranking → Top 5
                                           │
        ┌───────────────────┬──────────────┼──────────────┬───────────────────┐
        ▼                   ▼              ▼              ▼                   ▼
  [Sentiment]          [Outcome ML]   [Lime XAI]    [LLM Explainer]      [Agent Crew]
  RoBERTa Model        TF-IDF + LogReg Word Feature  Local / Groq /      Analyst → Predictor
  CardiffNLP           Impact Scoring  Importance    Claude / OpenAI /   → Fact Checker
                                                      Gemini
        └───────────────────┴──────────────┬──────────────┴───────────────────┘
                                           │
                                           ▼
                                [Redis Caching Layer]
                                           │
                                           ▼
                           [Flask Web Server & Dashboard]
                           REST APIs • D3.js Knowledge Graph
```

---

# 🛠️ Technology Stack

| Component | Tool / Library | Purpose |
| :--- | :--- | :--- |
| **Live News Ingestion** | `feedparser` | Fetch live RSS article feeds |
| **Historical Ingestion** | `httpx` + `tenacity` | Async GDELT DOC 2.0 & NewsAPI connectors with retry-on-429/5xx |
| **Normalized Schema** | `pydantic` | `models.news_schema.Article` — shared shape across all ingestion sources |
| **Deduplication** | MD5 Hashing | Article uniqueness verification across RSS + GDELT + NewsAPI |
| **NLP & NER** | SpaCy (`en_core_web_sm`) | Text cleaning & Named Entity Recognition |
| **Embeddings** | `all-MiniLM-L6-v2` | SentenceTransformer vector generation |
| **Vector Storage** | ChromaDB | Local persistent vector database |
| **Sparse Retrieval** | `rank-bm25` | Keyword-based BM25 search |
| **Reranking** | `ms-marco-MiniLM-L-6-v2` | CrossEncoder relevance reranker |
| **Sentiment Analysis** | RoBERTa (`twitter-roberta-base-sentiment-latest`) | Deep learning sentiment classification |
| **Impact Prediction** | TF-IDF + Logistic Regression / Rule Engine | ML impact classifier with fallback |
| **Explainable AI** | LIME (`lime`) | Word-level feature attribution |
| **Multi-Agent System** | LangGraph (`langgraph`) | Analyst → Predictor → Fact Checker pipeline |
| **LLM Inference** | Ollama, Groq, Anthropic, OpenAI, or Gemini | Selectable per query via `langchain` + `litellm` |
| **Knowledge Graph** | NetworkX & D3.js | Entity relationship network building & visualization |
| **Caching Layer** | Redis (`redis-py`) | Query-result caching + API-response caching, both TTL-based |
| **Web Server & UI** | Flask, HTML5, CSS3, JavaScript, D3.js | REST API & Interactive UI Dashboard |
| **Evaluation** | Custom RAG Metrics | Faithfulness, Relevancy, Precision, Recall |
| **Testing** | `pytest` + `pytest-asyncio` | Mocked-HTTP unit tests for ingestion connectors |
| **Packaging** | `uv` | Dependency resolution & locking (`pyproject.toml` / `uv.lock`) |

---

# 📁 Project Structure

```text
News-Analysis-and-Outcome-Analyzer/
├── main.py                     # CLI entry point (full pipeline & query loop)
├── server.py                   # Flask backend server providing REST APIs
├── ingestion_runner.py         # Orchestrates RSS + async GDELT/NewsAPI ingestion, dedup, preprocessing, embeddings
├── pyproject.toml              # Project dependencies (uv)
├── uv.lock                     # Locked dependency versions
├── Dockerfile                  # Container build instructions
├── docker-compose.yml          # Multi-container orchestrator (Flask + Redis)
├── start.sh                    # Startup wrapper script
├── .env.example                # Sample environment variables configuration
│
├── ingestion/                  # News ingestion module
│   ├── __init__.py
│   ├── news_fetcher.py         # Multi-feed RSS parser with deduplication
│   ├── base_connector.py       # Abstract BaseNewsConnector interface
│   ├── gdelt_connector.py      # GDELT DOC 2.0 API connector (async, retried, cached)
│   └── newsapi_connector.py    # NewsAPI /v2/everything connector (async, retried, cached, paginated)
│
├── preprocessing/              # NLP preprocessing module
│   ├── __init__.py
│   └── preprocess.py           # SpaCy text cleaner & NER entity tagger
│
├── embeddings/                 # Vector database module
│   ├── __init__.py
│   └── embed_store.py          # SentenceTransformer & ChromaDB manager
│
├── retrieval/                  # Hybrid search module
│   ├── __init__.py
│   └── search.py               # BM25 + Vector Search + CrossEncoder Reranker
│
├── models/                     # AI & ML inference models + shared schemas
│   ├── __init__.py             # Intentionally lightweight — see note below
│   ├── news_schema.py          # Pydantic Article schema, shared by every ingestion source
│   ├── sentiment.py            # RoBERTa sentiment classifier
│   ├── outcome.py              # ML impact classifier (TF-IDF + LogReg) & fallback
│   ├── llm_explainer.py        # LLM explanation via the guardrail/tracing graph
│   └── outcome_model/          # Serialized ML model artifacts
│
├── llm/                        # LLM provider routing
│   └── providers.py            # litellm-based call_llm() for /api/analyze + LangChain _build_model() for the agent crew
│
├── agents/                     # Multi-agent framework
│   ├── __init__.py
│   └── news_crew.py            # Analyst, Predictor, Fact-Checker agents (LangGraph)
│
├── xai/                        # Explainable AI module
│   ├── __init__.py
│   └── lime_explainer.py       # LIME word importance calculator
│
├── cache/                      # Performance caching layer
│   ├── __init__.py
│   ├── redis_cache.py          # LLM /api/analyze result cache
│   └── api_cache.py            # Raw GDELT/NewsAPI response cache (separate keyspace/TTL)
│
├── knowledge_graph/            # Entity network graph module
│   ├── __init__.py
│   └── graph_builder.py        # Co-occurrence entity graph builder
│
├── guardrails/                 # LangGraph safety pipeline wrapping LLM calls
│   ├── graph.py                # before-hook → HITL interrupt → LLM call → after-hook
│   └── pii.py                  # PII detection/redaction
│
├── observability/               # Tracing
│   └── tracing.py              # trace_llm_call — LangSmith if configured, local fallback otherwise
│
├── evaluation/                 # RAG evaluation benchmark
│   ├── __init__.py
│   ├── ragas_eval.py           # Precision, recall, relevancy & faithfulness metrics
│   ├── eval_runner.py          # Command line evaluation runner
│   └── results.json            # Metric evaluation output
│
├── notebooks/                  # Training notebooks & scripts
│   └── train_outcome_model.py  # Trainer script for outcome ML model
│
├── static/                     # Web dashboard frontend
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── tests/
│   ├── __init__.py
│   └── test_ingestion.py       # Mocked-HTTP unit tests for GDELT/NewsAPI connectors
│
├── data/                       # Raw & processed JSON news data (gitignored, generated locally)
└── storage/                    # Persistent ChromaDB vector storage (gitignored, generated locally)
```

> **Note on `models/__init__.py`:** it intentionally does **not** re-export `analyze_sentiment` / `predict_outcome` / `explain`. Those pull in heavyweight ML pipelines at import time, and every consumer already imports them directly from their own submodule (`from models.sentiment import analyze_sentiment`, etc.) — re-exporting them here would force anything touching `models.*`, including the lightweight `Article` schema, to eagerly load a RoBERTa model. Keep new additions to this file minimal for the same reason.

---

# ⚙️ Installation & Setup

## Prerequisites

* **Python:** 3.14+ (see `pyproject.toml` → `requires-python`)
* **[uv](https://docs.astral.sh/uv/)** — dependency management for this project
* **Ollama:** Installed locally ([ollama.com](https://ollama.com/download)) if you want the local LLM provider
* **Redis:** Optional (for caching, automatically falls back gracefully if absent)
* **Storage:** ~6 GB free space (for local ML models & vector storage)

---

## 1. Clone Repository

```bash
git clone https://github.com/Likeshkumarsahu/News-Analysis-and-Outcome-Analyzer.git
cd News-Analysis-and-Outcome-Analyzer
```

---

## 2. Install Dependencies (`uv`)

```bash
uv sync
```

This creates `.venv/` and installs everything pinned in `uv.lock`. Activate it with `source .venv/bin/activate`, or just prefix commands with `uv run` (used throughout this README) and skip activation entirely.

---

## 3. Download SpaCy NLP Model

```bash
uv run python -m spacy download en_core_web_sm
```

---

## 4. Configure Ollama (Local LLM Engine)

Install and run Ollama, then pull the target model:

```bash
ollama pull llama3.2:3b
ollama serve
```

---

## 5. Configure Environment Variables (`.env`)

Create a `.env` file in the project root:

```env
# ── Network & Host ──────────────────────────────────────────
OLLAMA_HOST=http://localhost:11434
PORT=5000

# ── Redis Caching (optional — degrades gracefully if unset) ──
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_TTL_SECONDS=3600
API_CACHE_TTL_SECONDS=21600

# ── Cloud LLM providers (all optional — pick what you use) ───
# Used either by the website's per-query provider picker, or as
# server-side fallback keys in llm/providers.py's FALLBACK_CHAIN.
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# ── Agent crew defaults (used when no per-query provider is sent) ──
CREW_PROVIDER=local
CREW_MODEL=llama3.2:3b

# ── Historical ingestion ──────────────────────────────────────
NEWS_API_KEY=your_newsapi_key_here          # free tier: newsapi.org/register
INGEST_QUERIES=India,world news             # comma-separated
INGEST_LOOKBACK_DAYS=2

# ── Observability (optional) ──────────────────────────────────
LANGSMITH_API_KEY=your_langsmith_key_here

# ── HuggingFace offline mode ──────────────────────────────────
TRANSFORMERS_OFFLINE=1
HF_HUB_OFFLINE=1
```

---

# 🚀 Running the Project

## Option A — Web Dashboard (Recommended)

### Step 1: Run the Ingestion Pipeline
Fetches RSS + historical (GDELT/NewsAPI) news, preprocesses entities, and generates ChromaDB embeddings:

```bash
uv run ingestion_runner.py
```

### Step 2: Launch Web Server

```bash
uv run server.py
```

Open your browser at `http://localhost:5000`.

---

## Option B — Command Line Interface (CLI)

```bash
uv run main.py                                                          # full pipeline + interactive prompt loop
uv run main.py --skip-ingest --query "India economic growth outlook"    # query directly, skip ingestion
```

---

## Option C — Docker Deployment (Flask + Redis)

```bash
docker-compose up --build
```

Access the application at `http://localhost:5000` (or `http://localhost:5001`).

---

## Option D — Run RAG Evaluation Metrics

```bash
uv run evaluation/eval_runner.py
```

---

## Option E — Run Tests

```bash
uv run pytest tests/ -v
```

Ingestion connector tests use mocked HTTP responses — no live API keys or network access required.

---

# 🌐 REST API Specifications

### 1. Analyze Query
`POST /api/analyze`
Runs hybrid retrieval, sentiment analysis, ML impact prediction, LIME XAI, and LLM explanation.

* **Payload:**
```json
{
  "query": "India Pakistan diplomatic relations",
  "provider": "local",
  "llm_model": null,
  "api_key": null
}
```
`provider` is one of `local | groq | anthropic | openai | gemini`. For any provider other than `local`, also send `llm_model` (see `GET /api/llm/providers` for the current selectable list per provider) and `api_key`.

* **Response:**
```json
{
  "query": "India Pakistan diplomatic relations",
  "provider": "local",
  "sentiment": { "label": "NEGATIVE", "confidence": 0.892 },
  "outcome": {
    "impact": "HIGH",
    "confidence": 0.85,
    "matched": ["tension", "border", "military"],
    "explanation": "ML model predicts HIGH impact..."
  },
  "explanation": "Based on retrieved news sources...",
  "llm_meta": { "provider_used": "Local (Ollama)", "model_used": "ollama/llama3.2:3b", "latency_ms": 1830, "cost_usd": 0.0 },
  "xai": {
    "sentiment": { "top_words": [["tension", -0.42], ["border", -0.31]] },
    "outcome": { "top_words": [["military", 0.51], ["conflict", 0.44]] }
  },
  "articles": [],
  "_cached": false
}
```

---

### 2. Live News Ingestion
`POST /api/ingest`
Triggers RSS fetch, SpaCy NER extraction, and ChromaDB vector updates.

---

### 3. Multi-Agent Deep Analysis
`POST /api/crew`
Runs the 3-agent LangGraph pipeline (Analyst → Predictor → Fact Checker) on whichever provider/model you send — same `provider`/`llm_model`/`api_key` fields as `/api/analyze`. Omit them (or send `provider: "local"`) to use the `CREW_PROVIDER`/`CREW_MODEL` server defaults.

---

### 4. LLM Provider Discovery
* `GET /api/llm/status` — Ollama connectivity + model availability.
* `GET /api/llm/providers` — Selectable provider/model list (Local, Groq, Anthropic, OpenAI, Gemini) for the frontend's provider picker.

---

### 5. Knowledge Graph Endpoints
* `GET /api/graph` — Retrieve co-occurrence nodes and edges.
* `POST /api/graph/rebuild` — Force rebuild of entity graph from processed news.

---

### 6. Other Utility Endpoints
* `GET /api/status` — Database count statistics.
* `POST /api/explain` — Compute custom LIME explanation for arbitrary text.
* `GET /api/cache/status` & `POST /api/cache/clear` — Check or flush Redis query cache.
* `POST /api/evaluate` — Execute RAG evaluation suite via API.

---

# 📊 Evaluation Benchmark Results

Evaluated on standard domain-specific test sets using custom RAG metrics:

| Metric | Score | Description |
| :--- | :---: | :--- |
| **Context Precision** | **0.733** | Proportion of retrieved context chunks directly relevant to query |
| **Context Recall** | **0.353** | Coverage of ground-truth signals by retrieved documents |
| **Answer Relevancy** | **Evaluated** | Alignment between generated LLM response and input query |
| **Faithfulness** | **Evaluated** | Factual grounding of generated answer within context |
| **Overall Score** | **0.271+** | Aggregate performance benchmark |

---

# 💡 Core System Highlights

* **Hybrid Search Strategy:** Combines the strengths of lexical precision (BM25) and semantic intent (`all-MiniLM-L6-v2`), capped by CrossEncoder re-ranking (`ms-marco-MiniLM-L-6-v2`) to eliminate retrieval noise.
* **Explainable AI (LIME):** Word-level token attribution gives clear visibility into why RoBERTa flagged sentiment or why the ML model scored high impact.
* **Multi-Agent Orchestration:** A LangGraph pipeline runs autonomous agents that cross-check findings and fact-check predictions before generating the final report.
* **Flexible LLM Backend:** Toggle per query between fully private local execution (`llama3.2:3b` via Ollama) or any of four cloud providers (Groq, Claude, OpenAI, Gemini) — with automatic fallback across the chain if your first choice fails.
* **Historical + Live Ingestion:** RSS covers the last 24–48 hours; GDELT and NewsAPI extend coverage backward for genuine historical analysis, all deduplicated into one corpus.

---

# ⚠️ Known Limitations & Considerations

* RSS feeds primarily capture real-time headlines (past 24–48 hours) — use the GDELT/NewsAPI connectors for historical coverage.
* NewsAPI's free tier caps at 100 requests/day and roughly a 1-month lookback window; GDELT has no such limit and is the better source for older history.
* Ollama local LLM execution requires ~4 GB free RAM.
* LIME explanations use sampling approximations for fast execution speed.
* Running the 3-agent Deep Analysis pipeline on a paid cloud provider makes several LLM calls per query (one per agent, plus tool-calling turns) — costs more than a single `/api/analyze` call.

---

# 🔮 Future Roadmap

* [ ] Advanced graph neural network (GNN) entity link prediction
* [ ] Real-time WebSocket streaming news alerts
* [ ] Multi-language news translation and sentiment analysis
* [ ] User authentication & workspace state persistence

---

# 👨‍💻 Author

**Likesh Kumar Sahu**
*6th Semester Computer Science / AI-ML Engineering Student*
GitHub: [github.com/Likeshkumarsahu](https://github.com/Likeshkumarsahu)

---

# 📄 License