# 📰 Newsana AI — News Analysis & Outcome Analyzer

A real-time, Retrieval-Augmented Generation (RAG) based news analysis and outcome forecasting system. It collects live news from multiple global RSS feeds, indexes documents in ChromaDB, builds entity Knowledge Graphs, performs hybrid search (BM25 + Semantic + CrossEncoder Reranking), classifies sentiment via RoBERTa, predicts event impact using Machine Learning (TF-IDF + Logistic Regression with rule-based fallback), explains decisions using Explainable AI (LIME), orchestrates multi-agent tasks via CrewAI, accelerates responses with Redis caching, and generates natural language insights through local LLMs (Ollama Llama 3.2) or Cloud APIs (Groq).

> **6th Semester Engineering Project**  
> AI/ML Pipeline • RAG • Knowledge Graph • CrewAI Agents • XAI • Local LLM / Groq • Redis • Flask Dashboard

---

## 🔍 Overview

Newsana AI provides an end-to-end intelligence framework designed to digest raw, fast-moving news streams and transform them into structured, actionable, and explainable insights. 

### Key Capabilities

* **Live Multi-Source Ingestion:** Automated fetching across 9 major global & regional RSS feeds (BBC, Al Jazeera, Reuters, The Hindu, NDTV, India Today, Times of India, Hindustan Times, Economic Times).
* **Smart Deduplication & Preprocessing:** MD5 hash hashing prevents storing duplicate articles, followed by SpaCy NLP text cleaning and Named Entity Recognition (NER).
* **Persistent Vector & Graph Indexing:** Chunks articles into ChromaDB vector storage (`all-MiniLM-L6-v2`) and extracts entity co-occurrence Knowledge Graphs using NetworkX.
* **Hybrid Search Engine:** Combines sparse BM25 keyword matching with dense semantic vector search, followed by a CrossEncoder reranker (`ms-marco-MiniLM-L-6-v2`) for optimal precision.
* **RoBERTa Sentiment Analysis:** Micro-fine-grained sentiment classification (POSITIVE, NEGATIVE, NEUTRAL) with confidence scores using Cardiff NLP's RoBERTa.
* **Machine Learning Impact Classifier:** Predicts event impact severity (HIGH, MEDIUM, LOW) using a trained TF-IDF + Logistic Regression model with automatic rule-based signal fallback.
* **Explainable AI (LIME XAI):** Computes word-level feature importance for sentiment and impact predictions to eliminate black-box AI opacity.
* **Multi-Agent Architecture (CrewAI):** Sequential execution of 3 autonomous agents (Senior News Analyst, Strategic Intelligence Analyst, Editorial Fact Checker) for deep research dossiers.
* **Dual-Engine LLM Explainer:** Local CPU-friendly generation via Ollama (`llama3.2:3b`) or cloud inference using free Groq models (Llama 3.3, Llama 3.1, Gemma 2, Mixtral).
* **Redis Caching & Fast Response:** Query-level caching layer to instantly return recurring analysis results.
* **Interactive Modern Web Dashboard:** Rich Flask-backed interface featuring dynamic gauges, Chart.js analytics, D3.js Knowledge Graph visualization, and real-time controls.
* **Automated RAG Evaluation:** Built-in quantitative metric calculator measuring Context Precision, Context Recall, Answer Relevancy, and Faithfulness.

---

# 🏗️ System Architecture

```text
               ┌────────────────────────────────────────────────────────┐
               │         RSS News Sources (9 Feeds / Global & Regional)  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
                         [Ingestion Engine] feedparser + MD5 Hash
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
  [Sentiment]          [Outcome ML]   [Lime XAI]     [LLM Engine]         [CrewAI Agents]
  RoBERTa Model        TF-IDF + LogReg Word Feature   Ollama Llama 3.2    Analyst → Predictor
  CardiffNLP           Impact Scoring  Importance    or Groq Cloud       → Fact Checker
        └───────────────────┴──────────────┬──────────────┴───────────────────┘
                                           │
                                           ▼
                                [Redis Caching Layer]
                                           │
                                           ▼
                           [Flask Web Server & Dashboard]
                           REST APIs • Chart.js • D3.js
```

---

# 🛠️ Technology Stack

| Component | Tool / Library | Purpose |
| :--- | :--- | :--- |
| **News Ingestion** | `feedparser` | Fetch live RSS article feeds |
| **Deduplication** | MD5 Hashing | Article uniqueness verification |
| **NLP & NER** | SpaCy (`en_core_web_sm`) | Text cleaning & Named Entity Recognition |
| **Embeddings** | `all-MiniLM-L6-v2` | SentenceTransformer vector generation |
| **Vector Storage** | ChromaDB | Local persistent vector database |
| **Sparse Retrieval** | `rank-bm25` | Keyword-based BM25 search |
| **Reranking** | `ms-marco-MiniLM-L-6-v2` | CrossEncoder relevance reranker |
| **Sentiment Analysis** | RoBERTa (`twitter-roberta-base-sentiment-latest`) | Deep learning sentiment classification |
| **Impact Prediction** | TF-IDF + Logistic Regression / Rule Engine | ML impact classifier with fallback |
| **Explainable AI** | LIME (`lime`) | Word-level feature attribution |
| **Multi-Agent System** | CrewAI (`crewai`) | Autonomous agent orchestration |
| **LLM Inference** | Ollama (`llama3.2:3b`) & Groq API | Local or cloud natural language synthesis |
| **Knowledge Graph** | NetworkX & D3.js | Entity relationship network building & visualization |
| **Caching Layer** | Redis (`redis-py`) | High-speed response caching with TTL |
| **Web Server & UI** | Flask, HTML5, CSS3, JavaScript, Chart.js | REST API & Interactive UI Dashboard |
| **Evaluation** | Custom RAG Metrics | Faithfulness, Relevancy, Precision, Recall |

---

# 📁 Project Structure

```text
News-Analysis-and-Outcome-Analyzer/
├── main.py                     # CLI entry point (full pipeline & query loop)
├── server.py                   # Flask backend server providing REST APIs
├── ingestion_runner.py         # Standalone news ingestion script
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Project configuration
├── Dockerfile                  # Container build instructions
├── docker-compose.yml          # Multi-container orchestrator (Flask + Redis)
├── start.sh                    # Startup wrapper script
├── .env.example                # Sample environment variables configuration
│
├── ingestion/                  # News fetcher module
│   ├── __init__.py
│   └── news_fetcher.py         # Multi-feed RSS parser with deduplication
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
├── models/                     # AI & ML inference models
│   ├── __init__.py
│   ├── sentiment.py            # RoBERTa sentiment classifier
│   ├── outcome.py              # ML impact classifier (TF-IDF + LogReg) & fallback
│   ├── llm_explainer.py        # Ollama local & Groq cloud LLM explainer
│   └── outcome_model/          # Serialized ML model artifacts
│
├── agents/                     # CrewAI multi-agent framework
│   ├── __init__.py
│   └── news_crew.py            # Senior Analyst, Strategic Predictor, Fact-Checker agents
│
├── xai/                        # Explainable AI module
│   ├── __init__.py
│   └── lime_explainer.py       # LIME word importance calculator
│
├── cache/                      # Performance caching layer
│   ├── __init__.py
│   └── redis_cache.py          # Redis connection & cache manager
│
├── knowledge_graph/            # Entity network graph module
│   ├── __init__.py
│   └── graph_builder.py        # Co-occurrence entity graph builder
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
│   ├── index.html              # Single Page Application HTML
│   ├── style.css               # Modern glassmorphism & dark-mode styling
│   ├── script.js               # Frontend controller & API integrator
│   └── assets/                 # Icons, JS utilities, and mock data
│
├── data/                       # Raw & processed JSON news data
└── storage/                    # Persistent ChromaDB vector storage
```

---

# ⚙️ Installation & Setup

## Prerequisites

* **Python:** 3.10 or 3.11
* **Ollama:** Installed locally ([ollama.com](https://ollama.com/download))
* **Redis:** Optional (for caching, automatically falls back gracefully if absent)
* **Storage:** ~6 GB free space (for local ML models & vector storage)

---

## 1. Clone Repository

```bash
git clone https://github.com/Likeshkumarsahu/News-Analysis-and-Outcome-Analyzer.git
cd News-Analysis-and-Outcome-Analyzer
```

---

## 2. Environment Setup

### Option A — Standard Virtual Environment (`venv`)

```bash
python3 -m venv venv312
source venv312/bin/activate
```

### Option B — Using `uv` (Fast)

```bash
uv venv venv312
source venv312/bin/activate
```

---

## 3. Install PyTorch CPU & Dependencies

Install PyTorch CPU first to keep installation lightweight:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Then install remaining requirements:

```bash
pip install -r requirements.txt
```

---

## 4. Download SpaCy NLP Model

```bash
python -m spacy download en_core_web_sm
```

---

## 5. Configure Ollama (Local LLM Engine)

Install and run Ollama, then pull the target Llama 3.2 3B model:

```bash
# Pull lightweight local model
ollama pull llama3.2:3b

# Start Ollama service
ollama serve
```

---

## 6. Configure Environment Variables (`.env`)

Create a `.env` file in the project root:

```env
# Network & Host Settings
OLLAMA_HOST=http://localhost:11434
PORT=5000

# Redis Cache Settings (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_TTL_SECONDS=3600

# Optional Groq Cloud API Key (for cloud LLM mode)
GROQ_API_KEY=your_groq_api_key_here

# HuggingFace Offline Flags (optional)
TRANSFORMERS_OFFLINE=0
HF_DATASETS_OFFLINE=0
```

---

# 🚀 Running the Project

## Option A — Web Dashboard (Recommended)

### Step 1: Run Ingestion & Indexing Pipeline
Fetch raw news, preprocess entities, and generate ChromaDB embeddings:

```bash
python ingestion_runner.py
```

### Step 2: Launch Web Server

```bash
python server.py
```

Open your browser and navigate to:

```text
http://localhost:5000
```

---

## Option B — Command Line Interface (CLI)

### Run Full Pipeline & Interactive Prompt Loop

```bash
python main.py
```

### Query Directly (Skip Ingestion)

```bash
python main.py --skip-ingest --query "India economic growth outlook"
```

### Single Direct Query Execution

```bash
python main.py --skip-ingest --query "Global oil price trends"
```

---

## Option C — Docker Deployment (Flask + Redis)

Deploy using Docker Compose with built-in Redis caching:

```bash
docker-compose up --build
```

Access the application at `http://localhost:5000` (or `http://localhost:5001`).

---

## Option D — Run RAG Evaluation Metrics

Run automated quantitative evaluation over query test suites:

```bash
python evaluation/eval_runner.py
```

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
  "groq_model": "llama-3.3-70b-versatile",
  "groq_api_key": "optional_groq_key"
}
```

* **Response:**
```json
{
  "query": "India Pakistan diplomatic relations",
  "provider": "local",
  "sentiment": {
    "label": "NEGATIVE",
    "confidence": 0.892
  },
  "outcome": {
    "impact": "HIGH",
    "confidence": 0.85,
    "matched": ["tension", "border", "military"],
    "explanation": "ML model predicts HIGH impact..."
  },
  "explanation": "Based on retrieved news sources...",
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
Triggers live RSS fetch, SpaCy NER extraction, and ChromaDB vector updates.

---

### 3. CrewAI Multi-Agent Workflow
`POST /api/crew`  
Runs the 3-agent autonomous intelligence process (Analyst → Predictor → Fact Checker).

---

### 4. Knowledge Graph Endpoints
* `GET /api/graph` — Retrieve co-occurrence nodes and edges.
* `POST /api/graph/rebuild` — Force rebuild of entity graph from processed news.

---

### 5. Other Utility Endpoints
* `GET /api/status` — Get database count statistics.
* `POST /api/explain` — Compute custom LIME explanation for arbitrary text.
* `GET /api/llm/status` — Verify Ollama connectivity and list supported Groq models.
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
* **Multi-Agent Orchestration:** CrewAI orchestrates autonomous agents that cross-check findings and fact-check predictions before generating the final report.
* **Flexible LLM Backend:** Seamlessly toggle between fully private local execution (`llama3.2:3b` via Ollama) and ultra-fast cloud inference (Groq API).

---

# ⚠️ Known Limitations & Considerations

* RSS news feeds primarily capture real-time headlines (past 24–48 hours).
* Ollama local LLM execution requires ~4 GB free RAM.
* LIME explanations use sampling approximations for fast execution speed.

---

# 🔮 Future Roadmap

* [ ] Integration with historical news APIs (e.g., NewsAPI / GDELT)
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

This project is open-source software licensed under the **MIT License**.