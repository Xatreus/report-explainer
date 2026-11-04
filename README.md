# Report Explainer — Document Intelligence Platform

Turn a folder of reports into a searchable, evidence-aware intelligence workspace. Ingest PDF/TXT documents, search with semantic and lexical retrieval, compare extracted findings, inspect metrics and risks, and run a bounded report-analysis agent.

## Four capability layers

### Phase 1 — Semantic RAG
- Local sentence-transformer embeddings (default: all-MiniLM-L6-v2).
- Persistent chunk embeddings in SQLite.
- Dense vector similarity plus lexical ranking, fused using reciprocal-rank fusion.
- Optional cross-encoder reranking (default: ms-marco-MiniLM-L-6-v2).
- Source-aware Q&A with retrieved passages displayed for inspection.

### Phase 2 — Multi-document intelligence
- Upload up to 100 PDF/TXT reports per batch.
- Deduplicate identical normalized content.
- Search the whole workspace or selected reports.
- Compare extracted metrics and identify newly listed, shared, and no-longer-listed risk labels.
- Persist extracted analyses for repeat comparisons.

### Phase 3 — Document intelligence dashboard
- Extract entities, numeric metrics, risks, action items and limitations.
- Interactive metric charts and risk distribution charts.
- Tables grouped by report and entity.
- Metric comparisons retain units and periods; incompatible units are not treated as directly comparable.

### Phase 4 — Specialized report-analysis agent
- Bounded tool-calling loop with configurable maximum rounds.
- Allowlisted read-only tools: list reports, search reports, read report text.
- Execution trace and separate evidence-auditing pass.

## Architecture

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Extraction | pypdf |
| Chunking | Overlapping word-window chunks |
| Embeddings | sentence-transformers |
| Vector storage | SQLite JSON vectors, cosine similarity |
| Hybrid retrieval | Dense similarity + lexical ranking + reciprocal-rank fusion |
| Reranking | Optional Sentence Transformers CrossEncoder |
| LLM | OpenAI SDK / compatible chat-completions provider |
| Analytics | JSON-structured extraction |
| Dashboard | Plotly, pandas |
| Agent | Bounded function calling and evidence verification |
| Tests | pytest, GitHub Actions |

SQLite keeps setup manageable. The current vector index scans stored vectors in-process; it is suitable for a small portfolio workspace, not a high-throughput corpus. A dedicated vector database or ANN index can replace this layer later.

## Quick start

Python 3.11+ is recommended. Semantic models run locally and may download several hundred MB on first use.

1. Clone the repository: https://github.com/Xatreus/report-explainer
2. Create a virtual environment: python -m venv .venv
3. Activate it (PowerShell: .venv\\Scripts\\Activate.ps1; macOS/Linux: source .venv/bin/activate).
4. Install core dependencies: python -m pip install --upgrade pip && python -m pip install -r requirements.txt
5. Install semantic models: python -m pip install -r requirements-ml.txt
6. Copy .env.example to .env and configure the settings below.
7. Run: streamlit run app.py
8. Test: python -m pytest -q

The core requirements keep CI lightweight. The optional ML requirements install PyTorch/Transformers through sentence-transformers and may take longer or require substantial disk space. If PyTorch installation is platform-specific, install the appropriate CPU or CUDA build first, then install requirements-ml.txt.

Configuration:

    OPENAI_API_KEY=your_key
    OPENAI_BASE_URL=
    OPENAI_MODEL=gpt-4o-mini
    EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
    REPORT_DB_PATH=data/report_explainer.db

## How to use

1. Open Workspace & upload, select PDF/TXT files, and ingest them.
2. Open Semantic search & Q&A, ask a question, inspect retrieved passages, and generate a cited answer.
3. Use Compare reports to select baseline and later reports. Structured extraction is cached locally.
4. Open Intelligence dashboard to inspect entities, metrics and risk distribution.
5. Open Analysis agent, describe a cross-report objective, then inspect the tool trace and evidence-checked answer.

## Privacy, safety and limitations

- Reports, extracted analyses and embeddings are stored locally in SQLite at data/report_explainer.db by default. Do not commit this database.
- Embedding and reranking models run locally after download. Initial model downloads require internet access.
- LLM calls send report text, selected passages, or tool results to the configured provider. Review provider data terms before processing confidential documents.
- The agent has an allowlist of read-only tools and a bounded call loop. It cannot execute arbitrary code or take external actions.
- Prompt injection remains a risk. Documents are untrusted input; prompt instructions are defense-in-depth, not a security boundary.
- Model-generated metrics and risk labels require human review. Source IDs point to stored chunks; they do not prove a claim.
- This is still a portfolio application, not a hardened multi-tenant service. Security helpers and PostgreSQL tenant policies are present, but Streamlit login, persisted user management, end-to-end RBAC, quotas, encrypted backups and a production threat review remain unfinished.

## Known limitations

- OCR requires the optional Python packages plus system Tesseract and Poppler binaries; if unavailable, extraction falls back to selectable PDF text.
- SQLite vector search is an exact scan, not an approximate-nearest-neighbor index.
- Lexical search is simple; multilingual retrieval depends on model and tokenization quality.
- Supported scale units are normalized, but currencies and fiscal periods are not converted or reconciled.
- Semantic risk matches are similarity candidates requiring human review, not proof of equivalent or resolved risks.
- Dashboard charts require structured analyses to be generated.
- Agent verification is another model call, not a formal proof.

## Next engineering improvements

Complete production identity integration and end-to-end RBAC; build a labelled retrieval benchmark; add encrypted backups, key rotation and operational monitoring; evaluate semantic risk matching against human-labelled pairs; reconcile fiscal periods and financial statement definitions.


## Next-stage infrastructure

The next engineering layer is available as optional modules so the default SQLite demo remains easy to run.

### OCR and page-aware citations
- document_pipeline.py extracts selectable PDF text page-by-page and attempts OCR on sparse pages.
- Chunks retain page_start, page_end, and whether text came from PDF extraction or OCR.
- The SQLite workspace stores this provenance and displays the page beside retrieved passages.
- Install requirements-ocr.txt and the system Tesseract + Poppler binaries to enable OCR. Without them, selectable PDF text still works.

### PostgreSQL + pgvector
- postgres_store.py is the optional tenant-scoped vector backend. It creates pgvector embeddings and an HNSW cosine index.
- It enables and forces PostgreSQL row-level security on report, chunk, and audit tables. Application queries also filter by tenant.
- The document/chunk foreign key includes tenant ID; deterministic IDs are tenant-scoped.
- Requires PostgreSQL with pgvector installed and permission to create the extension. Configure DATABASE_URL.
- The current Streamlit default remains SQLite. Use the background ingestion option to write to PostgreSQL; this is a separate deployment path, not an automatic migration of existing SQLite data.

### Background ingestion and batching
- ingestion_worker.py provides Redis/RQ enqueue and worker functions for PDF/TXT files.
- DocumentStore.ingest batches local embedding calls. The PostgreSQL worker embeds chunks in bounded batches (EMBED_BATCH_SIZE).
- Install requirements-worker.txt, configure REDIS_URL and TENANT_ID, and run an RQ worker with rq worker reports.
- Treat Redis as trusted infrastructure: restrict network access and credentials. Do not expose tenant ID as an unauthenticated client-controlled field.

### Retrieval evaluation
retrieval_eval.py computes Recall@k, MRR and nDCG@k. Use query IDs mapped to ranked chunk IDs and graded relevance judgments (qrels) to evaluate a test set. These are metrics utilities; a representative, human-labelled evaluation dataset still needs to be created before reporting real retrieval quality.

### Security, access control and encryption
- security.py provides PBKDF2 password hashing, HMAC-signed expiring sessions, role-permission checks, Fernet text encryption/decryption and audit-event insertion.
- PostgreSQL stores report and chunk text encrypted when FERNET_KEY is configured. Generate and back up this key securely; losing it makes encrypted text unrecoverable.
- The PostgreSQL schema includes tenant-aware row-level security and audit events. Worker ingestion writes an audit record.
- These are security building blocks, not a complete production identity system: the Streamlit app does not yet have a user-registration/login UI or a persisted user directory, and every UI action is not yet wired through RBAC. A production deployment must validate identity server-side, derive tenant IDs from the authenticated principal, use a restricted database role, enforce TLS, rotate secrets, and review backups/logs.

### Semantic risk and normalized metric comparison
- Risk matching uses local sentence embeddings when the optional ML stack is installed, with a fuzzy lexical fallback. Matches include a score and require human review.
- Metric comparison normalizes supported scales (for example thousand/million USD, bytes and time units). It deliberately does not convert between currencies or incompatible units without a trusted exchange-rate source.
- Extracted values and periods still require review; matching names alone do not establish accounting equivalence.

### Optional installation

    python -m pip install -r requirements-ml.txt
    python -m pip install -r requirements-ocr.txt
    python -m pip install -r requirements-prod.txt
    python -m pip install -r requirements-worker.txt

The OCR package also requires Tesseract and Poppler installed at the operating-system level. PostgreSQL requires a pgvector-enabled server. Keep core requirements.txt lightweight for local tests and the basic SQLite app.

## License

No license is currently declared. Unless a license is added, standard copyright restrictions apply.
