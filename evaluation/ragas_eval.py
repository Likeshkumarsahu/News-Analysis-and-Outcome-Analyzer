import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import json
import re
from retrieval.search import search
from models.sentiment import analyze_sentiment
from models.outcome import predict_outcome
from models.llm_explainer import explain


EVAL_QUERIES = [
    {
        "question": "What is the current situation between India and Pakistan?",
        "ground_truth": "tension military diplomatic conflict border",
    },
    {
        "question": "What is happening with inflation and economic policy?",
        "ground_truth": "inflation economy policy trade growth",
    },
    {
        "question": "What are the latest developments in US foreign policy?",
        "ground_truth": "US diplomatic foreign policy asia relations",
    },
    {
        "question": "Are there any natural disasters reported recently?",
        "ground_truth": "earthquake flood disaster emergency relief",
    },
    {
        "question": "What is the status of India US relations?",
        "ground_truth": "india us relations trade security cooperation",
    },
]


# ── Metric functions ──────────────────────────────────────────────────────────

def _tokenize(text: str) -> set:
    return set(re.findall(r'\b\w+\b', text.lower()))


def context_precision(contexts: list[str], question: str) -> float:
    """
    What fraction of retrieved chunks are relevant to the question?
    Relevance = word overlap between chunk and question > threshold.
    """
    if not contexts:
        return 0.0
    q_tokens = _tokenize(question)
    relevant = 0
    for ctx in contexts:
        ctx_tokens = _tokenize(ctx)
        overlap = len(q_tokens & ctx_tokens) / max(len(q_tokens), 1)
        if overlap > 0.1:
            relevant += 1
    return round(relevant / len(contexts), 3)


def context_recall(contexts: list[str], ground_truth: str) -> float:
    """
    How much of the ground truth is covered by retrieved context?
    """
    if not contexts:
        return 0.0
    gt_tokens  = _tokenize(ground_truth)
    all_ctx    = _tokenize(" ".join(contexts))
    covered    = gt_tokens & all_ctx
    return round(len(covered) / max(len(gt_tokens), 1), 3)


def answer_relevancy(answer: str, question: str) -> float:
    """
    How relevant is the answer to the question?
    Word overlap between answer and question keywords.
    """
    if not answer or "unavailable" in answer.lower():
        return 0.0
    q_tokens  = _tokenize(question)
    a_tokens  = _tokenize(answer)
    overlap   = len(q_tokens & a_tokens) / max(len(q_tokens), 1)
    return round(min(overlap * 2, 1.0), 3)   # scale up, cap at 1.0


def faithfulness(answer: str, contexts: list[str]) -> float:
    """
    Is the answer grounded in the retrieved context?
    Fraction of answer sentences that have word overlap with context.
    """
    if not answer or "unavailable" in answer.lower():
        return 0.0
    sentences  = [s.strip() for s in answer.split(".") if len(s.strip()) > 10]
    if not sentences:
        return 0.0
    ctx_tokens = _tokenize(" ".join(contexts))
    grounded   = 0
    for sent in sentences:
        sent_tokens = _tokenize(sent)
        overlap = len(sent_tokens & ctx_tokens) / max(len(sent_tokens), 1)
        if overlap > 0.15:
            grounded += 1
    return round(grounded / len(sentences), 3)


# ── Main evaluation ───────────────────────────────────────────────────────────

def run_evaluation(save_path: str = "evaluation/results.json") -> dict:
    os.makedirs("evaluation", exist_ok=True)

    all_scores = {
        "faithfulness":      [],
        "answer_relevancy":  [],
        "context_recall":    [],
        "context_precision": [],
    }

    print(f"\n  Running {len(EVAL_QUERIES)} eval queries...\n")

    for i, item in enumerate(EVAL_QUERIES, 1):
        question     = item["question"]
        ground_truth = item["ground_truth"]

        print(f"  [{i}/{len(EVAL_QUERIES)}] {question[:55]}...")

        # Retrieve
        results = search(question, top_k=3)
        if not results:
            print("    No results — skipping.\n")
            continue

        contexts = [r["text"] for r in results]

        # Generate answer
        sentiment = analyze_sentiment(results[0]["text"])
        outcome   = predict_outcome(results[0]["text"])
        answer    = explain(
            query=question,
            retrieved_articles=results,
            sentiment=sentiment,
            outcome=outcome,
        )

        # Score
        cp = context_precision(contexts, question)
        cr = context_recall(contexts, ground_truth)
        ar = answer_relevancy(answer, question)
        f  = faithfulness(answer, contexts)

        all_scores["context_precision"].append(cp)
        all_scores["context_recall"].append(cr)
        all_scores["answer_relevancy"].append(ar)
        all_scores["faithfulness"].append(f)

        print(f"    precision={cp} recall={cr} relevancy={ar} faith={f}\n")

    if not all_scores["faithfulness"]:
        print("  No scores computed.")
        return {}

    # Average across queries
    final = {
        k: round(sum(v) / len(v), 3)
        for k, v in all_scores.items()
    }
    final["overall"] = round(sum(final.values()) / len(final), 3)

    # Save
    output = {"scores": final, "samples": len(all_scores["faithfulness"])}
    with open(save_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  Saved to {save_path}")
    return final


def print_scores(scores: dict) -> None:
    print("\n" + "="*50)
    print("  EVALUATION RESULTS")
    print("="*50)
    print(f"  Faithfulness:      {scores.get('faithfulness',      0):.3f}  (answer grounded in context?)")
    print(f"  Answer Relevancy:  {scores.get('answer_relevancy',  0):.3f}  (answer on topic?)")
    print(f"  Context Recall:    {scores.get('context_recall',    0):.3f}  (context covers ground truth?)")
    print(f"  Context Precision: {scores.get('context_precision', 0):.3f}  (context relevant to query?)")
    print("-"*50)
    print(f"  Overall Score:     {scores.get('overall',           0):.3f}")
    print("="*50)


if __name__ == "__main__":
    scores = run_evaluation()
    if scores:
        print_scores(scores)