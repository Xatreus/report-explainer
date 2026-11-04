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
- This is a portfolio application, not a hardened multi-tenant service. Authentication, authorization, encryption-at-rest, quotas, background workers, backups and tenant isolation are not implemented.

## Known limitations

- OCR for scanned PDFs is not included.
- SQLite vector search is an exact scan, not an approximate-nearest-neighbor index.
- Lexical search is simple; multilingual retrieval depends on model and tokenization quality.
- Metric comparisons are name-matched and unit-aware but do not normalize currencies or fiscal periods.
- Risk comparison detects matching labels, not semantic equivalence or proof that a risk disappeared.
- Dashboard charts require structured analyses to be generated.
- Agent verification is another model call, not a formal proof.

## Next engineering improvements

OCR and page-aware citations; PostgreSQL + pgvector or Qdrant; background ingestion and batch embedding; retrieval evaluation (Recall@k, MRR, nDCG); authentication, RBAC, encryption, audit logging and tenant isolation; semantic risk matching and normalized financial metric comparison.

## License

No license is currently declared. Unless a license is added, standard copyright restrictions apply.
