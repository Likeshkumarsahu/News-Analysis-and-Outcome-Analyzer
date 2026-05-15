import spacy

# load once
nlp = spacy.load("en_core_web_sm")

def get_entities(text):
    doc = nlp(text)

    entities = {
        "PERSON": [],
        "ORG": [],
        "GPE": [],   # countries, cities
    }

    for ent in doc.ents:
        if ent.label_ in entities:
            entities[ent.label_].append(ent.text)

    # remove duplicates
    for key in entities:
        entities[key] = list(set(entities[key]))

    return entities