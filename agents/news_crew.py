import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from retrieval.search import search
from models.sentiment import analyze_sentiment
from models.outcome import predict_outcome
import ollama

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL       = "ollama/llama3.2:3b"

# ── Custom Tools ──────────────────────────────────────────────────────────────

@tool("News Search Tool")
def news_search_tool(query: str) -> str:
    """
    Search for relevant news articles from the database.
    Returns top 5 articles with title, source, and summary.
    """
    results = search(query, top_k=5)
    if not results:
        return f"No articles found for query: {query}"

    output = []
    for i, r in enumerate(results, 1):
        output.append(
            f"Article {i}:\n"
            f"  Title:   {r['title']}\n"
            f"  Source:  {r['source']}\n"
            f"  Summary: {r['text'][:300]}\n"
            f"  Score:   {r['score']:.3f}"
        )
    return "\n\n".join(output)


@tool("Sentiment Analysis Tool")
def sentiment_tool(text: str) -> str:
    """
    Analyze sentiment of a news text.
    Returns POSITIVE, NEGATIVE, or NEUTRAL with confidence score.
    """
    result = analyze_sentiment(text)
    return (
        f"Sentiment: {result['label'].upper()}\n"
        f"Confidence: {result['confidence']:.1%}"
    )


@tool("Impact Prediction Tool")
def impact_tool(text: str) -> str:
    """
    Predict the impact level of news: HIGH, MEDIUM, or LOW.
    Returns impact level, confidence, and key signals.
    """
    result = predict_outcome(text)
    return (
        f"Impact: {result['impact']}\n"
        f"Confidence: {result['confidence']:.1%}\n"
        f"Signals: {', '.join(result['matched']) if result['matched'] else 'none'}"
    )


# ── Agents ────────────────────────────────────────────────────────────────────

def create_analyst_agent():
    """
    Agent 1: News Analyst
    Retrieves relevant articles and summarizes the current situation.
    """
    return Agent(
        role="Senior News Analyst",
        goal="Find and analyze the most relevant news articles for the given query. "
             "Provide a clear, factual summary of the current situation.",
        backstory=(
            "You are an experienced news analyst with 15 years of experience "
            "covering global events. You specialize in finding relevant information "
            "quickly and presenting it in a clear, unbiased manner."
        ),
        tools=[news_search_tool, sentiment_tool],
        verbose=True,
        allow_delegation=False,
        llm=MODEL,
    )


def create_predictor_agent():
    """
    Agent 2: Outcome Predictor
    Predicts likely outcomes and consequences based on the news analysis.
    """
    return Agent(
        role="Strategic Intelligence Analyst",
        goal="Based on the news analysis provided, predict the most likely outcomes "
             "and consequences. Assess the impact level and explain your reasoning.",
        backstory=(
            "You are a strategic intelligence analyst who specializes in predicting "
            "geopolitical, economic, and social outcomes based on current news events. "
            "You base your predictions on factual evidence and historical patterns."
        ),
        tools=[impact_tool],
        verbose=True,
        allow_delegation=False,
        llm=MODEL,
    )


def create_critic_agent():
    """
    Agent 3: Fact Checker & Critic
    Validates the analysis and predictions, checks for bias or errors.
    """
    return Agent(
        role="Editorial Fact Checker",
        goal="Review the analysis and predictions from other agents. "
             "Identify any potential biases, factual errors, or overstatements. "
             "Provide a balanced final assessment.",
        backstory=(
            "You are a rigorous fact-checker and editorial critic with expertise "
            "in media literacy and bias detection. You ensure all analysis is "
            "grounded in facts and presents multiple perspectives fairly."
        ),
        tools=[news_search_tool],
        verbose=True,
        allow_delegation=False,
        llm=MODEL,
    )


# ── Tasks ─────────────────────────────────────────────────────────────────────

def create_tasks(query: str, analyst, predictor, critic):
    """Create tasks for each agent."""

    task_analyze = Task(
        description=(
            f"Search for news articles about: '{query}'\n"
            f"1. Use the News Search Tool to find relevant articles\n"
            f"2. Use the Sentiment Analysis Tool on the top article\n"
            f"3. Summarize the current situation in 3-4 sentences\n"
            f"4. List the key facts and entities involved"
        ),
        expected_output=(
            "A structured analysis containing:\n"
            "- Current situation summary (3-4 sentences)\n"
            "- Sentiment assessment with confidence\n"
            "- Key facts and entities\n"
            "- Top 3 most relevant article titles and sources"
        ),
        agent=analyst,
    )

    task_predict = Task(
        description=(
            f"Based on the analysis of '{query}' provided by the Senior News Analyst:\n"
            f"1. Use the Impact Prediction Tool to assess impact level\n"
            f"2. Predict 3 likely short-term outcomes (next 1-4 weeks)\n"
            f"3. Predict 2 likely long-term consequences (next 3-6 months)\n"
            f"4. Rate the overall severity: LOW / MEDIUM / HIGH / CRITICAL"
        ),
        expected_output=(
            "A prediction report containing:\n"
            "- Impact level with confidence\n"
            "- 3 short-term outcome predictions\n"
            "- 2 long-term consequence predictions\n"
            "- Severity rating with justification"
        ),
        agent=predictor,
        context=[task_analyze],
    )

    task_critique = Task(
        description=(
            f"Review the analysis and predictions about '{query}':\n"
            f"1. Verify key claims by searching for additional sources\n"
            f"2. Identify any potential bias or missing perspectives\n"
            f"3. Provide a balanced final verdict\n"
            f"4. Write a concise executive summary (max 150 words)"
        ),
        expected_output=(
            "A critical review containing:\n"
            "- Verification status of key claims\n"
            "- Identified biases or gaps (if any)\n"
            "- Alternative perspectives considered\n"
            "- Executive summary (max 150 words)"
        ),
        agent=critic,
        context=[task_analyze, task_predict],
    )

    return [task_analyze, task_predict, task_critique]


# ── Main Crew Runner ──────────────────────────────────────────────────────────

def run_news_crew(query: str) -> dict:
    """
    Run the full multi-agent CrewAI pipeline for a news query.

    Returns:
        {
            "query":          str,
            "analysis":       str,   ← Analyst output
            "predictions":    str,   ← Predictor output
            "critique":       str,   ← Critic output
            "final_summary":  str,   ← Executive summary
        }
    """
    print(f"\n🤖 Starting CrewAI pipeline for: '{query}'")

    # Create agents
    analyst  = create_analyst_agent()
    predictor = create_predictor_agent()
    critic   = create_critic_agent()

    # Create tasks
    tasks = create_tasks(query, analyst, predictor, critic)

    # Assemble crew
    crew = Crew(
        agents=[analyst, predictor, critic],
        tasks=tasks,
        process=Process.sequential,   # Analyst → Predictor → Critic
        verbose=True,
    )

    # Run
    result = crew.kickoff()

    # Parse outputs
    outputs = {}
    for i, task_output in enumerate(crew.tasks):
        key = ["analysis", "predictions", "critique"][i]
        outputs[key] = str(task_output.output) if hasattr(task_output, "output") else ""

    return {
        "query":         query,
        "analysis":      outputs.get("analysis", ""),
        "predictions":   outputs.get("predictions", ""),
        "critique":      outputs.get("critique", ""),
        "final_summary": str(result),
    }