# 📰 News Analysis & Outcome Analyzer

A real-time, Retrieval-Augmented Generation (RAG) based news analysis system that fetches live news, performs sentiment analysis, predicts impact levels, explains decisions using Explainable AI (XAI), and generates natural language insights through a local Large Language Model (LLM) — all running locally on CPU without external APIs.

> **6th Semester Engineering Project**
> AI/ML Pipeline • RAG • XAI • Local LLM • Flask Dashboard

---

## 🔍 Overview

The system continuously collects news articles from multiple trusted sources, stores them in a vector database, retrieves relevant information using hybrid search techniques, analyzes sentiment and impact, generates explainable predictions, and presents results through a web interface.

### Key Capabilities

* Fetches live news from RSS feeds
* Performs Named Entity Recognition (NER) and preprocessing
* Stores embeddings in ChromaDB
* Hybrid retrieval using BM25 + Semantic Search + CrossEncoder reranking
* Sentiment analysis using RoBERTa
* Impact prediction (HIGH / MEDIUM / LOW)
* Explainable AI using LIME
* Natural language explanations using Mistral 7B via Ollama
* Evaluation using custom RAG metrics
* Interactive Flask-based dashboard

---

# 🏗️ System Architecture

```text
RSS Feeds (BBC, Al Jazeera, Reuters, The Hindu, NDTV)
                        ↓
              [Ingestion] feedparser
              dedup via MD5 hash
                        ↓
           [Preprocessing] SpaCy NER
           clean + extract entities
                        ↓
         ┌──────────────┴──────────────┐
         ↓                             ↓
  [ChromaDB]                   [Knowledge Graph]
  all-MiniLM-L6-v2              NetworkX entities
  vector embeddings
         └──────────────┬──────────────┘
                        ↓
           [Hybrid Retrieval]
           BM25 keyword search (top 20)
         + Semantic vector search (top 20)
         + CrossEncoder reranking → top 5
                        ↓
         ┌──────────────┼──────────────┐
         ↓              ↓              ↓
   [Sentiment]    [Outcome]       [LLM]
   RoBERTa        Rule-based      Ollama
   transformer    signals         Mistral 7B
                  scoring         (local)
         └──────────────┼──────────────┘
                        ↓
                [LIME XAI]
           word-level explanations
           for sentiment + impact
                        ↓
              ┌─────────┴─────────┐
              ↓                   ↓
         [Flask UI]         [Evaluation]
         Dashboard          RAG Metrics
```

---

# 🛠️ Technology Stack

| Component          | Tool/Library                            | Purpose                       |
| ------------------ | --------------------------------------- | ----------------------------- |
| News Ingestion     | feedparser                              | RSS feed collection           |
| Deduplication      | MD5 Hashing                             | Prevent duplicate articles    |
| NLP Processing     | SpaCy (`en_core_web_sm`)                | NER & text cleaning           |
| Embeddings         | all-MiniLM-L6-v2                        | Semantic vector generation    |
| Vector Database    | ChromaDB                                | Persistent vector storage     |
| Keyword Search     | rank-bm25                               | Sparse retrieval              |
| Reranking          | CrossEncoder (`ms-marco-MiniLM-L-6-v2`) | Relevance optimization        |
| Sentiment Analysis | RoBERTa                                 | News sentiment classification |
| Impact Prediction  | Rule-Based Engine                       | Transparent impact scoring    |
| Explainability     | LIME                                    | Word-level feature importance |
| LLM                | Ollama + Mistral 7B                     | Natural language explanations |
| Knowledge Graph    | NetworkX                                | Entity relationship graph     |
| Web Interface      | Flask + HTML/CSS/JS                     | Dashboard                     |
| Evaluation         | Custom Metrics                          | RAG performance assessment    |

---

# 📁 Project Structure

```text
Newsana/
├── main.py
├── server.py
├── ingestion_runner.py
├── requirements.txt
├── .env
│
├── ingestion/
│   ├── __init__.py
│   └── news_fetcher.py
│
├── preprocessing/
│   ├── __init__.py
│   └── preprocess.py
│
├── embeddings/
│   ├── __init__.py
│   └── embed_store.py
│
├── retrieval/
│   ├── __init__.py
│   └── search.py
│
├── models/
│   ├── __init__.py
│   ├── sentiment.py
│   ├── outcome.py
│   └── llm_explainer.py
│
├── xai/
│   ├── __init__.py
│   └── lime_explainer.py
│
├── evaluation/
│   ├── __init__.py
│   ├── ragas_eval.py
│   ├── eval_runner.py
│   └── results.json
│
├── static/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── data/
│   ├── raw_news.json
│   └── processed_news.json
│
└── storage/
    └── chroma/
```

---

# ⚙️ Installation

## Prerequisites

* Python 3.10+
* Ollama Installed
* ~6 GB Available Storage
* Internet Connection (First Run Only)

---

## 1. Clone Repository

```bash
git clone https://github.com/Likeshkumarsahu/News-Analysis-and-Outcome-Analyzer.git

cd News-Analysis-and-Outcome-Analyzer
```

---

## 2. Create Virtual Environment

### Using venv

```bash
python3 -m venv venv

source venv/bin/activate
```

### Using uv

```bash
uv venv venv

source venv/bin/activate
```

---

## 3. Install PyTorch CPU Build

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

---

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Download SpaCy Model

```bash
python -m spacy download en_core_web_sm
```

---

## 6. Setup Ollama + Mistral

Install Ollama:

https://ollama.com/download

Pull model:

```bash
ollama pull mistral:latest
```

Start Ollama:

```bash
ollama serve
```

---

## 7. Configure Environment Variables

Create a `.env` file:

```env
TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1
```

No API keys are required.

Everything runs locally through Ollama.

---

# 🚀 Running the Project

## Option A — Web Dashboard (Recommended)

### Step 1: Run Ingestion

```bash
python ingestion_runner.py
```

### Step 2: Start Server


```bash
ollama serve &
python server.py
```

Open:

```text
http://localhost:5000
```

---

## Option B — Command Line

### Full Pipeline

```bash
python main.py --query "India Pakistan tension"
```

### Skip Ingestion

```bash
python main.py --skip-ingest --query "India economic policy"
```

### Single Query

```bash
python main.py --skip-ingest --query "Gaza ceasefire"
```

---

## Option C — Evaluation

```bash
python evaluation/eval_runner.py
```

---

# 🌐 REST API

## Analyze Query

**POST**

```http
/api/analyze
```

### Example Request

```bash
curl -X POST http://localhost:5000/api/analyze \
-H "Content-Type: application/json" \
-d '{"query":"India Pakistan tension"}'
```

### Example Response

```json
{
  "query": "India Pakistan tension",
  "sentiment": {
    "label": "negative",
    "confidence": 0.697
  },
  "outcome": {
    "impact": "HIGH",
    "confidence": 0.80,
    "matched": [
      "tension",
      "conflict",
      "isolate"
    ]
  },
  "explanation": "Based on recent news...",
  "xai": {
    "sentiment": {
      "top_words": []
    },
    "outcome": {
      "top_words": []
    }
  },
  "articles": []
}
```

---

## Available Endpoints

| Method | Endpoint        | Description               |
| ------ | --------------- | ------------------------- |
| GET    | `/`             | Dashboard UI              |
| POST   | `/api/analyze`  | Analyze query             |
| POST   | `/api/ingest`   | Fetch latest news         |
| POST   | `/api/explain`  | Generate LIME explanation |
| POST   | `/api/evaluate` | Run evaluation metrics    |
| GET    | `/api/status`   | Database statistics       |

---

# 📊 Evaluation Metrics

| Metric            | Description                    | Score        |
| ----------------- | ------------------------------ | ------------ |
| Context Precision | Relevant retrieved chunks      | 0.733        |
| Context Recall    | Ground truth coverage          | 0.353        |
| Answer Relevancy  | Query-answer alignment         | Requires LLM |
| Faithfulness      | Grounding to retrieved context | Requires LLM |
| Overall Score     | Aggregate performance          | 0.271        |

> Answer relevancy and faithfulness require a functioning LLM connection.

---

# 💡 Core Features

## Hybrid Retrieval

Combines:

* BM25 keyword retrieval
* Semantic vector search
* CrossEncoder reranking

This significantly improves retrieval quality compared to vector-only approaches.

---

## Explainable AI (LIME)

Every prediction is accompanied by word-level explanations showing exactly which terms influenced the model's decision.

Benefits:

* Transparency
* Trustworthiness
* Debugging support

---

## Fully Local LLM

Powered by:

* Ollama
* Mistral 7B

Advantages:

* No API costs
* No rate limits
* Offline operation
* Privacy-friendly

---

## Incremental Processing Pipeline

The system is designed to be incremental.

Features:

* MD5-based article deduplication
* Persistent vector storage
* Re-runnable ingestion
* No duplicate embeddings

---

# ⚠️ Known Limitations

* RSS feeds typically provide only the most recent 24–48 hours of news.
* Mistral 7B requires approximately 4.5 GB RAM.
* Impact prediction is currently rule-based.
* LIME explanations are approximations (100 samples for faster execution).

---

# 🔮 Future Improvements

* [ ] Historical news support via NewsAPI
* [ ] Machine learning-based impact prediction
* [ ] Interactive knowledge graph visualization
* [ ] CrewAI multi-agent architecture
* [ ] User authentication and roles
* [ ] Docker deployment
* [ ] CI/CD pipeline integration
* [ ] Real-time streaming ingestion

---

# 👨‍💻 Author

**Likesh Kumar Sahu**

6th Semester Engineering Student

GitHub: https://github.com/Likeshkumarsahu

---

# 📄 License

This project is licensed under the MIT License.

Feel free to use, modify, and distribute it for academic or commercial purposes.
