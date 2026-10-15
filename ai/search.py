"""Kleine TF-IDF-ranking zonder modellen, downloads of vector-database."""

import math
import re
from collections import Counter

STOPWORDS = set("de het een en of ik je jij mijn me wil willen ben met in op voor van is zijn aan te meer over geen niet dat die graag studeer".split())


def _terms(text: str) -> list[str]:
    return [word for word in re.findall(r"[^\W_]{3,}", text.lower()) if word not in STOPWORDS]


def rank_minors(message: str, history: list[dict], minors: list[dict], limit: int = 12) -> list[dict]:
    """Rangschik; sluit bij nul woordoverlap geen minoren definitief uit.

    Recentere studentantwoorden wegen zwaarder. De LLM beoordeelt betekenis,
    ontkenningen en correcties; lexicale ranking bewijst geen relevantie.
    """
    if limit < 1:
        raise ValueError("Retrieval-limiet moet positief zijn.")
    query = Counter(_terms(message))
    for index, turn in enumerate(reversed(history)):
        if turn.get("role") == "user":
            for term in _terms(turn["content"]):
                query[term] += 1 / (index + 2)
    documents = [Counter(_terms(row["title"] + " " + row["description"])) for row in minors]
    frequency = Counter(term for document in documents for term in document)
    def score(document: Counter) -> float:
        return sum(query[term] * count * (math.log((1 + len(minors)) / (1 + frequency[term])) + 1)
                   for term, count in document.items()) / math.sqrt(sum(count * count for count in document.values()) or 1)
    # Stabiele sortering: bij gelijke score blijft bronvolgorde behouden.
    ranked = sorted(zip(minors, documents), key=lambda pair: score(pair[1]), reverse=True)
    return [row for row, _ in ranked[:limit]]
