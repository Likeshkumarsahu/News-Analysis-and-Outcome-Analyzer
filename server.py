from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
from retrieval.retrieve import search
from models.sentiment import get_sentiment
from models.outcome import predict_outcome
from models.llm_explainer import generate_llm_explanation

load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    query = data.get('query', '')

    if not query.strip():
        return jsonify({'error': 'Empty query'}), 400

    try:
        results = search(query, top_k=2)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        if not docs:
            return jsonify({'error': 'No results found'}), 404

        analysis_results = []
        for doc, meta in zip(docs, metas):
            sentiment = get_sentiment(doc)
            impact = predict_outcome(doc)
            
            try:
                explanation = generate_llm_explanation(doc, sentiment, impact, None)
            except Exception as e:
                explanation = "AI explanation unavailable due to technical issues."

            analysis_results.append({
                'content': doc,
                'sentiment': sentiment,
                'impact': impact,
                'source': meta.get('source', 'N/A'),
                'explanation': explanation
            })

        return jsonify({'results': analysis_results})

    except Exception as e:
        print(f"Error during analysis: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    app.run(debug=debug, port=port)
