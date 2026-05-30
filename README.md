# News Analysis & Outcome Analyzer

A RAG-based news analysis system with sentiment analysis, impact prediction, explainability (XAI), and LLM-generated insights.

## Architecture

## Tech Stack

| Component | Tool |
|---|---|
| News Ingestion | feedparser, newspaper3k |
| Preprocessing | SpaCy (en_core_web_sm) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector DB | ChromaDB |
| Retrieval | BM25 + CrossEncoder hybrid rerank |
| Sentiment | RoBERTa (cardiffnlp/twitter-roberta-base-sentiment-latest) |
| Impact | Rule-based keyword signals |
| LLM | Ollama + Mistral 7B (local) |
| XAI | LIME (word-level explanations) |
| Evaluation | Custom metrics (precision, recall, faithfulness, relevancy) |
| UI | Flask + HTML/CSS/JS |

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/Likeshkumarsahu/News-Analysis-and-Outcome-Analyzer.git
cd News-Analysis-and-Outcome-Analyzer
```

### 2. Create virtual environment
```bash
uv venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 4. Install and start Ollama
```bash
# Install Ollama from https://ollama.com
ollama pull mistral:latest
ollama serve
```

### 5. Environment variables
Create `.env` file:

### 6. Run ingestion
```bash
python ingestion_runner.py
```

### 7. Start web UI
```bash
python server.py
```
Open `http://localhost:5000`

### 8. CLI mode
```bash
python main.py --skip-ingest --query 'India Pakistan tension'
```

### 9. Run evaluation
```bash
python evaluation/eval_runner.py
```

## Project Structure
Newsana/
├── main.py                    # CLI entry point
├── server.py                  # Flask web server
├── ingestion_runner.py        # Pipeline runner
├── data/                      # Raw + processed news JSON
├── storage/                   # ChromaDB vector store
├── ingestion/                 # RSS feed fetcher
├── preprocessing/             # SpaCy NER + cleaning
├── embeddings/                # Sentence transformer + ChromaDB
├── retrieval/                 # BM25 + CrossEncoder hybrid search
├── models/                    # Sentiment, outcome, LLM explainer
├── xai/                       # LIME explainability
├── evaluation/                # Custom RAG evaluation metrics
└── static/                    # Flask frontend (HTML/CSS/JS)

## Evaluation Metrics

| Metric | Description |
|---|---|
| Context Precision | Fraction of retrieved chunks relevant to query |
| Context Recall | How much of ground truth is covered by context |
| Answer Relevancy | How relevant is LLM answer to the query |
| Faithfulness | How grounded is the answer in retrieved context |

## 6th Semester Project
Built as part of AI/ML curriculum — demonstrates end-to-end RAG pipeline
with explainable AI on real-time news data.