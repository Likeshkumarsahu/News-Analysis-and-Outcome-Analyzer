import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def chunk_text(text, size=200):
    words = text.split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]


def process_news():
    input_path = os.path.join(BASE_DIR, "data", "raw", "news.json")

    if not os.path.exists(input_path):
        print("No raw news found")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        news = json.load(f)

    processed = []

    for item in news:
        title = clean_text(item.get("title"))
        summary = clean_text(item.get("summary"))

        content = f"{title}. {summary}"
        chunks = chunk_text(content)

        processed.append({
            "source": item["source"],
            "title": title,
            "chunks": chunks,
            "published": item.get("published", ""),
            "topic": item.get("topic", "")
        })

    out_path = os.path.join(BASE_DIR, "data", "processed")
    os.makedirs(out_path, exist_ok=True)

    file_path = os.path.join(out_path, "processed_news.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(processed)} articles")

import spacy

# ---------- LOAD MODEL ----------
nlp = spacy.load("en_core_web_sm")

# ---------- ENTITY EXTRACTION ----------
def extract_entities(text):

    doc = nlp(text)

    entities = {
        "PERSON": [],
        "ORG": [],
        "GPE": []
    }

    for ent in doc.ents:

        if ent.label_ in entities:

            if ent.text not in entities[ent.label_]:
                entities[ent.label_].append(ent.text)

    return entities

# ---------- RUN ----------
if __name__ == "__main__":
    process_news()