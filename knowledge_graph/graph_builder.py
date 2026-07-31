import os
import json
from collections import defaultdict
from preprocessing.preprocess import load_processed

GRAPH_PATH = "data/knowledge_graph.json"


def build_graph() -> dict:
    """
    Build entity knowledge graph from processed_news.json.
    Nodes = entities, Edges = co-occurrence in same article.
    """
    articles = load_processed()
    if not articles:
        return {"nodes": [], "links": []}

    node_mentions = defaultdict(lambda: {"count": 0, "type": "OTHER"})
    edge_weight   = defaultdict(int)

    KEEP_TYPES = {"PERSON", "ORG", "GPE", "EVENT", "NORP", "FAC"}

    for article in articles:
        entities = article.get("entities", {})
        # Flatten all entities in this article
        article_ents = []
        for etype, enames in entities.items():
            if etype not in KEEP_TYPES:
                continue
            for name in enames:
                name = name.strip()
                if len(name) < 2 or len(name) > 40:
                    continue
                node_mentions[name]["count"] += 1
                node_mentions[name]["type"]   = etype
                article_ents.append(name)

        # Co-occurrence edges
        seen = list(set(article_ents))
        for i in range(len(seen)):
            for j in range(i+1, len(seen)):
                key = tuple(sorted([seen[i], seen[j]]))
                edge_weight[key] += 1

    # Filter: only nodes mentioned 2+ times
    valid_nodes = {n for n, v in node_mentions.items() if v["count"] >= 2}

    nodes = [
        {
            "id":       name,
            "type":     node_mentions[name]["type"],
            "mentions": node_mentions[name]["count"],
        }
        for name in valid_nodes
    ]

    links = [
        {
            "source": k[0],
            "target": k[1],
            "weight": w,
        }
        for k, w in edge_weight.items()
        if k[0] in valid_nodes and k[1] in valid_nodes and w >= 2
    ]

    graph = {"nodes": nodes, "links": links}

    os.makedirs("data", exist_ok=True)
    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f, indent=2)

    print(f"  Graph: {len(nodes)} nodes, {len(links)} edges → {GRAPH_PATH}")
    return graph


def load_graph() -> dict:
    if not os.path.exists(GRAPH_PATH):
        return build_graph()
    with open(GRAPH_PATH) as f:
        return json.load(f)