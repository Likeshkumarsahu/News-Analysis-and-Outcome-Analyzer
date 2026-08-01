from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

_analyzer   = AnalyzerEngine()
_anonymizer = AnonymizerEngine()

"""PII_ENTITIES = ["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
                 "US_SSN", "IN_AADHAAR", "IN_PAN", "PERSON", "LOCATION"]"""

PII_ENTITIES = ["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN", "IN_AADHAAR", "IN_PAN"]       


def scan_pii(text: str) -> list:
    """Return list of detected PII entities with type and confidence."""
    results = _analyzer.analyze(text=text, language="en", entities=PII_ENTITIES)
    return [{"type": r.entity_type, "score": round(r.score, 2),
             "start": r.start, "end": r.end} for r in results]


def redact_pii(text: str) -> dict:
    """
    Redact PII before it's sent to any external LLM provider.
    Returns {"text": redacted_text, "found": [...], "was_redacted": bool}
    """
    results = _analyzer.analyze(text=text, language="en", entities=PII_ENTITIES)
    if not results:
        return {"text": text, "found": [], "was_redacted": False}

    anonymized = _anonymizer.anonymize(text=text, analyzer_results=results)
    return {
        "text": anonymized.text,
        "found": [r.entity_type for r in results],
        "was_redacted": True,
    }