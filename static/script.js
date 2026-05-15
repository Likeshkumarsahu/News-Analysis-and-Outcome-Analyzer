document.addEventListener('DOMContentLoaded', () => {
    const queryInput = document.getElementById('queryInput');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loading = document.getElementById('loading');
    const resultsContainer = document.getElementById('resultsContainer');

    const analyze = async () => {
        const query = queryInput.value.trim();
        if (!query) {
            alert('Please enter a query');
            return;
        }

        resultsContainer.innerHTML = '';
        loading.classList.remove('hidden');

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query })
            });

            const data = await response.json();

            if (response.ok) {
                displayResults(data.results);
            } else {
                resultsContainer.innerHTML = `<p class="error">Error: ${data.error}</p>`;
            }
        } catch (error) {
            console.error('Fetch error:', error);
            resultsContainer.innerHTML = `<p class="error">Failed to connect to the server.</p>`;
        } finally {
            loading.classList.add('hidden');
        }
    };

    const displayResults = (results) => {
        resultsContainer.innerHTML = '';
        results.forEach((result, index) => {
            const sentimentBadge = getSentimentBadge(result.sentiment);
            
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h3>📰 News Result ${index + 1}</h3>
                <p>${result.content.substring(0, 400)}...</p>
                <hr>
                <div class="meta-info">
                    <span class="badge ${result.sentiment.toLowerCase()}">${sentimentBadge}</span>
                    <span>📊 Impact: ${result.impact}</span>
                </div>
                <p class="small">🌐 Source: ${result.source}</p>
                
                <div class="explanation-toggle" onclick="toggleExplanation(${index})">
                    <span>🧠 AI Analysis Reasoning</span>
                    <span id="arrow-${index}">▼</span>
                </div>
                <div id="explanation-${index}" class="explanation-content hidden">
                    <div class="explanation-box">${result.explanation}</div>
                </div>
            `;
            resultsContainer.appendChild(card);
        });
    };

    const getSentimentBadge = (sentiment) => {
        const s = sentiment.toLowerCase();
        if (s === 'positive') return '🟢 Positive';
        if (s === 'negative') return '🔴 Negative';
        return '🟡 Neutral';
    };

    window.toggleExplanation = (index) => {
        const content = document.getElementById(`explanation-${index}`);
        const arrow = document.getElementById(`arrow-${index}`);
        content.classList.toggle('hidden');
        arrow.textContent = content.classList.contains('hidden') ? '▼' : '▲';
    };

    analyzeBtn.addEventListener('click', analyze);
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') analyze();
    });
});
