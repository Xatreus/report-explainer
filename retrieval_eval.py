"""Offline retrieval metrics for ranked retrieval runs."""
from __future__ import annotations
import math
from collections.abc import Iterable, Sequence

def recall_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    if k < 1: raise ValueError("k must be at least 1")
    relevant_set = set(relevant)
    return len(set(retrieved[:k]) & relevant_set) / len(relevant_set) if relevant_set else 0.0

def reciprocal_rank(retrieved: Sequence[str], relevant: Iterable[str]) -> float:
    relevant_set = set(relevant)
    for rank, item in enumerate(retrieved, 1):
        if item in relevant_set: return 1.0 / rank
    return 0.0

def dcg_at_k(retrieved: Sequence[str], relevance: dict[str, float], k: int) -> float:
    if k < 1: raise ValueError("k must be at least 1")
    return sum(max(0.0, float(relevance.get(item, 0.0))) / math.log2(rank + 1)
               for rank, item in enumerate(retrieved[:k], 1))

def ndcg_at_k(retrieved: Sequence[str], relevance: dict[str, float], k: int) -> float:
    actual = dcg_at_k(retrieved, relevance, k)
    ideal_items = sorted(relevance, key=lambda item: float(relevance[item]), reverse=True)
    ideal = dcg_at_k(ideal_items, relevance, k)
    return actual / ideal if ideal else 0.0

def evaluate_run(retrieved: Sequence[str], relevance: dict[str, float], k: int = 5) -> dict[str, float]:
    relevant = {item for item, grade in relevance.items() if grade > 0}
    return {f"recall@{k}": recall_at_k(retrieved, relevant, k),
            "mrr": reciprocal_rank(retrieved, relevant), f"ndcg@{k}": ndcg_at_k(retrieved, relevance, k)}

def evaluate_dataset(runs: dict[str, Sequence[str]], qrels: dict[str, dict[str, float]], k: int = 5) -> dict[str, float]:
    ids = sorted(set(runs) & set(qrels))
    if not ids: raise ValueError("At least one query must have both a run and relevance labels.")
    rows = [evaluate_run(runs[qid], qrels[qid], k) for qid in ids]
    return {metric: sum(row[metric] for row in rows) / len(rows) for metric in rows[0]}
