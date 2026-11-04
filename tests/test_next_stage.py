import pytest

from analytics import compare_report_analyses, match_semantic_risks
from document_pipeline import chunk_page_records
from retrieval_eval import evaluate_run, evaluate_dataset, recall_at_k, reciprocal_rank, ndcg_at_k
from security import authorize, hash_password, issue_session_token, verify_password, verify_session_token


def test_retrieval_metrics_known_ranking():
    relevance = {"a": 3, "b": 0, "c": 1}
    assert recall_at_k(["b", "a"], {"a", "c"}, 2) == 0.5
    assert reciprocal_rank(["b", "a"], {"a", "c"}) == 0.5
    assert 0 < ndcg_at_k(["b", "a", "c"], relevance, 3) < 1
    assert evaluate_run(["a", "b"], relevance, 2)["mrr"] == 1.0


def test_retrieval_dataset_macro_average():
    result = evaluate_dataset({"q1": ["a"], "q2": ["x", "b"]},
                              {"q1": {"a": 1}, "q2": {"b": 1}}, k=2)
    assert result["recall@2"] == 1.0
    assert result["mrr"] == 0.75


def test_password_hash_and_session_integrity():
    encoded = hash_password("a-long-password-value")
    assert verify_password("a-long-password-value", encoded)
    assert not verify_password("wrong-password-value", encoded)
    token = issue_session_token("user-1", "tenant-1", "analyst", "test-secret")
    principal = verify_session_token(token, "test-secret")
    assert principal["tenant"] == "tenant-1"
    with pytest.raises(ValueError):
        verify_session_token(token + "tampered", "test-secret")


def test_rbac_denies_viewer_ingestion():
    with pytest.raises(PermissionError):
        authorize({"role": "viewer"}, "reports:ingest")
    authorize({"role": "admin"}, "reports:ingest")


def test_page_chunks_keep_page_provenance():
    pages = [{"page": 2, "text": " ".join(["revenue"] * 15), "extraction": "ocr"},
             {"page": 3, "text": " ".join(["risk"] * 15), "extraction": "text"}]
    chunks = chunk_page_records(pages, max_words=10, overlap=2)
    assert chunks[0]["page_start"] == 2
    assert chunks[-1]["page_start"] == 3
    assert chunks[0]["extraction"] == "ocr"


def test_metric_comparison_normalizes_scale_and_refuses_fx():
    left = {"metrics": [{"name": "Revenue", "value": 2, "unit": "million USD"}], "risks": []}
    right = {"metrics": [{"name": "Revenue", "value": 2500, "unit": "thousand USD"}], "risks": []}
    result = compare_report_analyses(left, right)["shared_metrics"][0]
    assert result["comparable"]
    assert result["earlier_normalized"] == 2_000_000
    assert result["later_normalized"] == 2_500_000
    foreign = compare_report_analyses(left, {"metrics": [{"name": "Revenue", "value": 2, "unit": "EUR"}], "risks": []})
    assert not foreign["shared_metrics"][0]["comparable"]


def test_semantic_risk_matching_is_reviewable():
    result = match_semantic_risks(
        [{"title": "Third-party supplier disruption"}],
        [{"title": "Disruption from suppliers"}],
        threshold=0.4,
    )
    assert len(result["matches"]) == 1
    assert result["matches"][0]["review_required"]
