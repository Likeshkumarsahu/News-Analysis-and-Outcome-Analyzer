# News Intelligence & Outcome Analyzer

AI-powered news analysis system that fetches global news, processes it, and provides sentiment analysis, impact prediction, and AI-driven reasoning using a Vector Database (ChromaDB) and Large Language Models (Gemini).

## 🚀 Features

- **Automated News Fetching:** Collects news from various RSS feeds (BBC, Reuters, etc.).
- **Vector Database Ingestion:** Stores news embeddings in ChromaDB for efficient retrieval.
- **Sentiment Analysis:** Categorizes news into Positive, Negative, or Neutral using RoBERTa.
- **Outcome Prediction:** Predicts the impact level (LOW, MEDIUM, HIGH) using a custom-trained model.
- **AI Reasoning Engine:** Generates detailed explanations and potential outcomes using Google's Gemini 2.5 Flash.
- **Dual Interface:** 
    - Web Interface (HTML/CSS/JS with Flask backend)
    - CLI Interface (`main.py`)

## 🛠️ Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Download SpaCy model:**
   ```bash
   python -m spacy download en_core_web_sm
   ```

3. **Set up API Keys:**
   - Create a `.env` file in the root directory.
   - Add your Gemini API key:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```

## 📂 Project Structure

- `main.py`: CLI entry point for fetching and querying.
- `server.py`: Flask backend for the web interface.
- `ingestion/`: Modules for RSS news fetching.
- `preprocessing/`: Text cleaning and entity extraction.
- `embeddings/`: ChromaDB integration and embedding storage.
- `retrieval/`: Search functionality for the Vector DB.
- `models/`:
    - `sentiment.py`: Sentiment analysis logic.
    - `outcome.py`: Impact prediction logic.
    - `llm_explainer.py`: Gemini-powered reasoning logic.
    - `outcome_model/`: Local weights for the outcome prediction model.
- `data/`: Raw and processed news storage.
- `static/`: HTML/CSS/JS files for the web interface.

## 🖥️ Usage

### Running the CLI
To update the news database and query via terminal:
```bash
python main.py
```

### Running the Web Interface
1. Start the Flask server:
   ```bash
   python server.py
   ```
2. Open `static/index.html` in your browser (or serve it via Flask).

## 📊 VDB Ingestion
To perform bulk ingestion of news from local JSON files:
```bash
python historical_ingestion.py
```
To build a clean Vector DB from RSS feeds:
```bash
python bulk_VDB_ingestion.py
```
