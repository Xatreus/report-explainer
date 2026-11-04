# Report Explainer

**Turn lengthy reports into answers you can inspect.**

Report Explainer is a local-first document intelligence workspace. Upload PDF and TXT reports, search across them, compare findings, explore extracted metrics and risks, and ask an AI analyst to explain what the documents actually say.

Built as a runnable portfolio project with a simple Streamlit interface and an optional AI provider. You can try the application without an API key; AI-generated explanations, comparisons and agent runs become available when you configure a provider and enter a model name supported by that provider in the sidebar.

<p align="center">
  <strong>PDF/TXT ingestion · Hybrid RAG · Page-aware evidence · Multi-report analysis · AI agent</strong>
</p>

## What you can do

| Capability | What it does |
|---|---|
| Explain a report | Upload a report or paste text; get a plain-language outline or AI explanation |
| Search your library | Find relevant passages across multiple reports using semantic + lexical retrieval |
| Evidence-grounded Q&A | Ask questions and inspect the passages and source IDs behind answers |
| Page-aware citations | Preserve PDF page numbers and show them alongside retrieved passages |
| Compare reports | Extract metrics, entities and risks, then compare two documents |
| Intelligence dashboard | Explore extracted financial metrics, entities and risk distributions |
| Report analyst | Run a bounded read-only agent that searches reports and checks its draft against retrieved evidence |
| OCR (optional) | Extract text from scanned PDF pages when Tesseract and Poppler are installed |

## Interface

The app is organized around six workspaces:

1. **Workspace & upload** — build and manage your local report library.
2. **Semantic search & Q&A** — retrieve passages and generate cited answers.
3. **Compare reports** — inspect differences between two reports.
4. **Intelligence dashboard** — view extracted metrics, risks and entities.
5. **Report analyst** — run a bounded tool-using analysis workflow.
6. **Explain one report** — the original single-report experience, including pasted text.

## Quick start

### 1. Requirements

- Python 3.11 or newer
- Git
- Internet access for the first installation and first download of local embedding models
- An LLM API key and model name are user-selected; any OpenAI-compatible chat-completions provider can be configured

### 2. Clone and create an environment

```bash
git clone https://github.com/Xatreus/report-explainer.git
cd report-explainer

python -m venv .venv
```

Activate it:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-ml.txt
```

The core requirements install the UI, PDF parsing, charts and tests. The ML requirements install Sentence Transformers for local embeddings and optional reranking. This package may install PyTorch and can take a while. For a CPU-only machine, install the appropriate CPU PyTorch build first if your platform requires it.

### 4. Configure the optional AI provider

Copy `.env.example` to `.env` and set:

```dotenv
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=
# Optional: prefill the model field in the app sidebar
OPENAI_MODEL=
```

Set `OPENAI_API_KEY` and optionally `OPENAI_BASE_URL` for your provider. Then enter the exact model identifier supported by that provider in the **Chat model** field in the app sidebar. There is no hard-coded default model: different providers expose different model names and capabilities. `OPENAI_MODEL` may be set in `.env` if you want to prefill that field, but it is optional. Leave the key and model empty to use local heuristic outlines and local retrieval features. No API key is needed to launch the app or index documents. AI explanations, generated answers, report comparisons and the report analyst require a configured chat-completions provider and a model.

### 5. Launch

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit (normally http://localhost:8501).

### 6. Run tests

```bash
python -m pytest -q
```

## First run walkthrough

Two fictional sample reports are included in `sample_reports/` so you can explore multi-report search and comparison immediately. Upload `northstar_q1.txt` and `northstar_q2.txt` from that folder in the workspace tab.

1. Open **Workspace & upload** and add a PDF or TXT report. You can select multiple reports.
2. Wait for local embeddings to be generated. The first run downloads the embedding model; later runs reuse the cached model.
3. Open **Semantic search & Q&A**, ask a question, and inspect the retrieved source passages.
4. If an API key is configured, generate an answer grounded in those passages.
5. Upload a second report and use **Compare reports** to extract and compare structured findings.
6. Explore the **Intelligence dashboard** and try the **Report analyst** on a cross-report question.
7. Use **Explain one report** for a quick explanation of a single PDF, TXT file or pasted text.

## How it works

```text
PDF / TXT
   |
   v
Text extraction ---- optional OCR for scanned PDF pages
   |
   v
Page-aware overlapping chunks
   |
   v
Local sentence-transformer embeddings
   |
   v
SQLite document + chunk store
   |
   v
Hybrid retrieval (dense + lexical) -> reciprocal-rank fusion
   |
   +--> optional cross-encoder reranking
   |
   +--> cited Q&A
   +--> multi-report structured extraction and comparison
   +--> dashboard
   +--> bounded report-analysis agent
```

### Main stack

- **Python 3.11+** — application and processing
- **Streamlit** — interactive web interface
- **pypdf** — PDF text extraction
- **Sentence Transformers** — local embeddings and optional reranking
- **SQLite** — local document, chunk, embedding and analysis storage
- **Plotly + pandas** — interactive charts and tables
- **OpenAI Python SDK** — OpenAI-compatible LLM integration
- **pytest + GitHub Actions** — automated tests

## Optional capabilities

The normal portfolio setup uses SQLite and does not require PostgreSQL, Redis, Docker, or an OCR system binary. The following are optional extensions.

### OCR for scanned PDFs

Install:

```bash
python -m pip install -r requirements-ocr.txt
```

Also install **Tesseract OCR** and **Poppler** for your operating system. The application attempts OCR on pages with little selectable text. If the optional OCR runtime is unavailable, selectable PDF text extraction remains available. OCR quality depends on scan quality and language packs.

### PostgreSQL + pgvector

Install:

```bash
python -m pip install -r requirements-prod.txt
```

Configure `DATABASE_URL` for a PostgreSQL server with pgvector installed. `postgres_store.py` provides an optional tenant-scoped vector store, HNSW index, row-level security policies, audit events and optional Fernet encryption. This is a separate backend path; it does not automatically migrate the default SQLite database.

### Redis background ingestion

Install:

```bash
python -m pip install -r requirements-worker.txt
```

Configure `REDIS_URL` and `DATABASE_URL`, then run an RQ worker:

```bash
rq worker reports
```

The worker supports PDF/TXT ingestion and bounded batch embeddings. These advanced modules are included for architecture exploration; the standard UI workflow uses local SQLite ingestion.

### Retrieval evaluation

`retrieval_eval.py` calculates:

- Recall@k
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (nDCG@k)

The functions accept ranked result IDs and relevance judgments. A representative, human-labelled benchmark dataset is needed before interpreting scores as actual system quality.

## Configuration reference

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | Optional LLM provider key | Empty |
| `OPENAI_BASE_URL` | Optional OpenAI-compatible endpoint | Provider default |
| `OPENAI_MODEL` | Optional initial value for the sidebar model field | Empty (user chooses) |
| `EMBEDDING_MODEL` | Local embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `RERANKER_MODEL` | Optional cross-encoder model | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `REPORT_DB_PATH` | Local SQLite database path | `data/report_explainer.db` |
| `DATABASE_URL` | Optional PostgreSQL connection | Not used by default |
| `REDIS_URL` | Optional worker queue | Not used by default |
| `FERNET_KEY` | Optional PostgreSQL text encryption key | Not used by default |

## Project structure

```text
report-explainer/
├── app.py                  # Streamlit application and UI
├── report_utils.py         # Text validation, chunking and local retrieval
├── document_pipeline.py    # Page-aware PDF extraction and optional OCR
├── document_store.py       # SQLite persistence and hybrid retrieval
├── analytics.py            # Structured report comparison and risk matching
├── analysis_agent.py       # Bounded read-only report analysis agent
├── retrieval_eval.py       # Recall@k, MRR and nDCG evaluation
├── security.py             # Reusable security primitives
├── postgres_store.py       # Optional PostgreSQL + pgvector backend
├── ingestion_worker.py     # Optional Redis/RQ ingestion worker
├── requirements.txt        # Core application dependencies
├── requirements-ml.txt     # Local embeddings and reranking
├── requirements-ocr.txt    # Optional OCR Python dependencies
├── requirements-prod.txt   # Optional PostgreSQL dependencies
├── requirements-worker.txt # Optional background worker dependencies
└── tests/                  # Unit and integration-style tests
```

## Privacy and limitations

- **Local by default:** uploaded documents, extracted analyses and embeddings are stored in the local SQLite database at `data/report_explainer.db`.
- **Local models:** embeddings and reranking run locally after model downloads.
- **External AI calls:** when an LLM provider is configured, report text or retrieved passages are sent to that provider for generation. Review its data policy before uploading confidential material.
- **Evidence matters:** generated summaries, extracted metrics and risk labels can be wrong. Inspect the original passage and source citation before relying on them.
- **Agent boundaries:** the report analyst has a bounded tool loop and read-only tools. This is not a guarantee against prompt injection or incorrect model output.
- **OCR:** scanned-page recognition depends on installed binaries, language packs and image quality.
- **Scale:** SQLite vector search is suitable for a personal or small portfolio workspace, not a large production corpus.
- **Financial comparisons:** supported scale units are normalized, but currencies and fiscal periods are not automatically reconciled.
- **Risk matching:** similarity scores identify candidate matches, not proof that two risks are identical or that a risk has been resolved.
- **Advanced backend:** PostgreSQL/RLS, Redis workers and security helpers are optional reference implementations, not a fully deployed multi-user service.

## Tests and CI

GitHub Actions runs the core test suite on Python 3.12 for pushes and pull requests. Optional OCR, PostgreSQL and Redis services are not required by the core CI job.

## License

This project is licensed under the [MIT License](LICENSE). You are free to use, modify, distribute and sublicense it subject to the license terms.
