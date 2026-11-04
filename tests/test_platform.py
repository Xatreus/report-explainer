import pytest

from analytics import compare_report_analyses, parse_json_object
from document_store import DocumentStore


class FakeEmbedder:
    def encode(self, texts, normalize_embeddings=True):
        return [[float('revenue' in text.lower()), float('risk' in text.lower()), 1.0] for text in texts]


class FakeReranker:
    def predict(self, pairs):
        return [1.0 if 'revenue' in text.lower() else 0.0 for _, text in pairs]


def test_parse_json_object_accepts_fenced_json():
    assert parse_json_object('```json\n{"ok": true}\n```') == {"ok": True}


def test_parse_json_object_rejects_array():
    with pytest.raises(ValueError):
        parse_json_object('[1, 2]')


def test_compare_report_analyses_tracks_metric_and_risk_changes():
    old = {"metrics": [{"name": "Revenue", "value": 10, "unit": "USD"}], "risks": [{"title": "Supply risk"}]}
    new = {"metrics": [{"name": "Revenue", "value": 12, "unit": "USD"}], "risks": [{"title": "Cyber risk"}]}
    result = compare_report_analyses(old, new)
    assert result["shared_metrics"][0]["later_value"] == 12
    assert result["new_risks"] == ["cyber risk"]
    assert result["risks_no_longer_listed"] == ["supply risk"]


def test_document_store_deduplicates_and_persists(tmp_path):
    store = DocumentStore(tmp_path / 'test.db', embedding_model=FakeEmbedder())
    text = 'Revenue increased during the quarter. ' * 60
    first = store.ingest('report.txt', text)
    duplicate = store.ingest('duplicate.txt', text)
    assert not first['duplicate']
    assert duplicate['duplicate']
    assert len(store.list_documents()) == 1
    assert store.get_document(first['id'])['file_name'] == 'report.txt'


def test_document_store_hybrid_search_and_reranking(tmp_path):
    store = DocumentStore(tmp_path / 'test.db', embedding_model=FakeEmbedder(), reranker=FakeReranker())
    store.ingest('revenue.txt', 'Revenue increased after launch. ' * 20)
    store.ingest('risk.txt', 'The report identifies supply chain risk. ' * 20)
    hits = store.search('revenue growth', top_k=3)
    assert hits and hits[0]['file_name'] == 'revenue.txt'
    assert 'rerank_score' in hits[0]


def test_document_store_delete(tmp_path):
    store = DocumentStore(tmp_path / 'test.db', embedding_model=FakeEmbedder())
    document = store.ingest('report.txt', 'Risk exposure increased. ' * 30)
    assert store.delete_document(document['id'])
    assert store.list_documents() == []
