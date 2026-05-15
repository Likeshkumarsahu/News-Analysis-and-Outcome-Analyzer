from transformers import pipeline

sentiment_model = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment"
)

def get_sentiment(text):
    result = sentiment_model(text)[0]

    label_map = {
        "LABEL_0": "NEGATIVE",
        "LABEL_1": "NEUTRAL",
        "LABEL_2": "POSITIVE"
    }

    return label_map[result["label"]]