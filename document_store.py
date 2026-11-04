"""Persistent multi-document vector store with hybrid retrieval and reranking."""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from report_utils import chunk_text, normalize_text
from document_pipeline import chunk_page_records


class DocumentStore:
    """SQLite-backed document store with local embeddings and cross-encoder reranking."""
    def __init__(self, db_path="data/report_explainer.db", embedding_model=None, reranker=None):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._embedding_model = embedding_model
        self._reranker = reranker
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as db:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("""CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, file_name TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE,
                text TEXT NOT NULL, uploaded_at TEXT NOT NULL, analysis_json TEXT)""")
            db.execute("""CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL, text TEXT NOT NULL, embedding_json TEXT NOT NULL,
                page_start INTEGER, page_end INTEGER, extraction TEXT NOT NULL DEFAULT 'text')""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(chunks)").fetchall()}
            for name, declaration in (("page_start", "INTEGER"), ("page_end", "INTEGER"),
                                      ("extraction", "TEXT NOT NULL DEFAULT 'text'")):
                if name not in columns:
                    db.execute(f"ALTER TABLE chunks ADD COLUMN {name} {declaration}")
            db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id)")

    def _embedder(self):
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("Semantic search requires sentence-transformers; install requirements-ml.txt.") from exc
            name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            self._embedding_model = SentenceTransformer(name)
        return self._embedding_model

    def _cross_encoder(self):
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError("Reranking requires sentence-transformers; install requirements.txt.") from exc
            name = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
            self._reranker = CrossEncoder(name)
        return self._reranker

    @staticmethod
    def _vector(value):
        return [float(x) for x in (value.tolist() if hasattr(value, "tolist") else value)]

    def ingest(self, file_name, text, pages=None, batch_size=32):
        normalized = normalize_text(text)
        if not normalized:
            raise ValueError("The document contains no extractable text.")
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        with self._connect() as db:
            old = db.execute("SELECT id, file_name FROM documents WHERE sha256=?", (digest,)).fetchone()
            if old:
                return {"id": old["id"], "file_name": old["file_name"], "duplicate": True, "chunks": 0}
        pieces = chunk_page_records(pages, max_words=220, overlap=40) if pages else chunk_text(normalized, max_words=220, overlap=40)
        if not pieces:
            raise ValueError("The document produced no searchable chunks.")
        vectors = []
        for start in range(0, len(pieces), batch_size):
            batch = pieces[start:start + batch_size]
            encoded = self._embedder().encode([p["text"] for p in batch], normalize_embeddings=True)
            vectors.extend(encoded)
        doc_id = digest[:16]
        with self._connect() as db:
            db.execute(
                "INSERT INTO documents (id,file_name,sha256,text,uploaded_at) VALUES (?,?,?,?,?)",
                (doc_id, file_name, digest, normalized, datetime.now(UTC).isoformat()))
            for index, (piece, vector) in enumerate(zip(pieces, vectors)):
                db.execute(
                    "INSERT INTO chunks (id,document_id,chunk_index,text,embedding_json,page_start,page_end,extraction) VALUES (?,?,?,?,?,?,?,?)",
                    (f"{doc_id}:S{index+1}", doc_id, index, piece["text"], json.dumps(self._vector(vector)),
                     piece.get("page_start"), piece.get("page_end"), piece.get("extraction", "text")))
        return {"id": doc_id, "file_name": file_name, "duplicate": False, "chunks": len(pieces)}

    def list_documents(self):
        with self._connect() as db:
            rows = db.execute("""SELECT d.id,d.file_name,d.uploaded_at,length(d.text) AS characters,
                (SELECT COUNT(*) FROM chunks c WHERE c.document_id=d.id) AS chunks,d.analysis_json
                FROM documents d ORDER BY d.uploaded_at DESC""").fetchall()
        return [dict(row) for row in rows]

    def get_document(self, doc_id):
        with self._connect() as db:
            row = db.execute("SELECT id,file_name,text,uploaded_at,analysis_json FROM documents WHERE id=?", (doc_id,)).fetchone()
        return dict(row) if row else None

    def delete_document(self, doc_id):
        with self._connect() as db:
            db.execute("PRAGMA foreign_keys = ON")
            cursor = db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            return cursor.rowcount > 0

    def save_analysis(self, doc_id, analysis):
        with self._connect() as db:
            db.execute("UPDATE documents SET analysis_json=? WHERE id=?", (json.dumps(analysis, ensure_ascii=False), doc_id))

    def search(self, query, top_k=6, document_ids=None, rerank=True):
        if not query.strip() or top_k < 1:
            return []
        params = []
        where = ""
        if document_ids is not None:
            if not document_ids:
                return []
            where = " WHERE c.document_id IN (" + ",".join("?" for _ in document_ids) + ")"
            params.extend(document_ids)
        with self._connect() as db:
            rows = db.execute(
                "SELECT c.id,c.document_id,c.chunk_index,c.text,c.embedding_json,c.page_start,c.page_end,c.extraction,d.file_name "
                "FROM chunks c JOIN documents d ON d.id=c.document_id" + where, params).fetchall()
        if not rows:
            return []
        import math
        query_vector = self._vector(self._embedder().encode([query], normalize_embeddings=True)[0])
        qnorm = math.sqrt(sum(x*x for x in query_vector)) or 1.0
        qterms = set(query.lower().split())
        token_sets = [set(row["text"].lower().split()) for row in rows]
        df = {term: sum(term in tokens for tokens in token_sets) for term in qterms}
        vectors, lexical = {}, {}
        for row, tokens in zip(rows, token_sets):
            vector = json.loads(row["embedding_json"])
            denom = qnorm * (math.sqrt(sum(x*x for x in vector)) or 1.0)
            vectors[row["id"]] = sum(a*b for a,b in zip(query_vector, vector)) / denom
            score = 0.0
            words = row["text"].lower().split()
            for term in qterms & tokens:
                freq = words.count(term)
                score += math.log(1 + (len(rows)-df[term]+0.5)/(df[term]+0.5)) * freq/(freq+1.2)
            lexical[row["id"]] = score
        fused = {}
        for ranking in (sorted(vectors, key=vectors.get, reverse=True), sorted(lexical, key=lexical.get, reverse=True)):
            for rank, chunk_id in enumerate(ranking, 1):
                fused[chunk_id] = fused.get(chunk_id, 0.0) + 1/(60+rank)
        by_id = {row["id"]: row for row in rows}
        candidate_ids = sorted(fused, key=fused.get, reverse=True)[:max(top_k*4, 12)]
        results = [{"id": cid, "document_id": by_id[cid]["document_id"],
                    "file_name": by_id[cid]["file_name"], "text": by_id[cid]["text"],
                    "page_start": by_id[cid]["page_start"], "page_end": by_id[cid]["page_end"],
                    "extraction": by_id[cid]["extraction"],
                    "vector_score": vectors[cid], "hybrid_score": fused[cid]} for cid in candidate_ids]
        if rerank and results:
            try:
                scores = self._cross_encoder().predict([(query, item["text"]) for item in results])
                for item, score in zip(results, scores):
                    item["rerank_score"] = float(score)
                results.sort(key=lambda item: item["rerank_score"], reverse=True)
            except (ImportError, RuntimeError):
                pass
        return results[:top_k]
