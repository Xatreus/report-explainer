# Report Explainer

**Turn dense reports into understandable, searchable, evidence-aware insights.** Upload a PDF or text file, ask questions in natural language, and explore key entities, metrics, risks, and action items.

Report Explainer is a focused Python application demonstrating practical GenAI, retrieval, source grounding, and document intelligence without unnecessary agent infrastructure.

## Features

- 📄 **PDF and TXT ingestion** — extract selectable PDF text, read text files, or paste content.
- 🧠 **Audience-aware explanations** — plain-language summaries tailored to readers, students, business leaders, technical readers, or researchers.
- 🌐 **Multilingual output** — English, Hindi, Arabic, and Urdu.
- 🔎 **Ask your report (RAG-style Q&A)** — chunk the document, retrieve relevant passages with a lightweight BM25-style lexical ranker, and answer questions using only retrieved context.
- 📌 **Source-grounded answers** — retrieved passages receive stable source IDs (for example, [S1]) that the model can cite and users can inspect.
- 🧾 **Structured report review** — extract key entities, important metrics, risks, action items, and missing information into a consistent format.
- 📴 **Local fallback** — generate a clearly labelled heuristic outline without an API key.
- ⬇️ **Markdown exports** — download explanations, question answers, and structured reviews.
- 🧪 **Automated tests** — regression tests cover normalization, validation, chunking, retrieval, and local fallback.

## Architecture and stack

| Layer | Implementation |
|---|---|
| UI | Streamlit |
| Language | Python |
| Document ingestion | pypdf, TXT |
| Text processing | Normalization, overlapping chunking |
| Retrieval | BM25-style lexical ranking (standard library) |
| Generation | OpenAI Python SDK with OpenAI-compatible chat-completions endpoints |
| Prompting | Grounded Q&A, structured extraction, audience-aware explanation |
| Configuration | python-dotenv |
| Quality | pytest, GitHub Actions |

The retrieval layer is intentionally lightweight and runs in memory. It does not require a vector database or embedding API, keeping setup simple and predictable. This is lexical retrieval, not semantic vector search.

## Quick start

### Requirements

- Python 3.11+
- An API key from a supported OpenAI-compatible provider for AI explanations, Q&A, and structured extraction (optional for local outline mode)

### 1. Clone

```bash
git clone https://github.com/Xatreus/report-explainer.git
cd report-explainer
```

### 2. Create a virtual environment

**Windows PowerShell**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure an AI provider (optional)

Copy `.env.example` to `.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o-mini
```

Use the base URL and model identifier documented by your provider. Leave `OPENAI_BASE_URL` empty for the default OpenAI endpoint. Never commit real API credentials; `.env` is ignored by Git.

Without a key, the app still supports a local heuristic outline. AI-powered Q&A and structured extraction require a configured provider.

### 5. Run

```bash
streamlit run app.py
```

### 6. Test

```bash
python -m pytest -q
```

## How retrieval works

1. Extract and normalize the uploaded report text.
2. Split it into overlapping passages and assign source IDs.
3. Tokenize the user's question and each passage.
4. Rank passages using a BM25-style lexical relevance score.
5. Send the highest-ranked passages to the model with instructions to answer only from those sources and cite their IDs.
6. Display the answer and the exact retrieved passages for inspection.

This is a small, transparent RAG-style pipeline. It uses lexical matching rather than embeddings, so it may miss relevant passages that use very different wording. The next retrieval upgrade could add embeddings and hybrid dense/sparse search.

## Project layout

```text
report-explainer/
├── app.py                    # Streamlit UI, explanation, Q&A, structured review
├── report_utils.py            # Extraction, normalization, chunking, retrieval, fallback
├── tests/
│   └── test_report_utils.py   # Unit and retrieval regression tests
├── .github/workflows/
│   └── tests.yml              # GitHub Actions test workflow
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Privacy, safety, and limitations

- Documents are processed in the current Streamlit session; there is no account system or persistent document database.
- AI features send the full report for explanation/extraction or selected passages for Q&A to the configured provider. Check its data-handling terms before using confidential information.
- Retrieval is lexical BM25-style ranking, not embedding-based semantic search; paraphrased queries may retrieve poorly.
- Source IDs identify retrieved text passages; they are not external references or proof that a model's interpretation is correct. Verify important claims against the original report.
- Report text is untrusted input. Prompt instructions reduce the risk of following embedded instructions but do not eliminate prompt injection.
- Scanned PDFs need OCR, which is not included.
- This is a portfolio/demo app, not a hardened document-processing service.

## Roadmap

- [ ] OCR for scanned PDFs
- [ ] Embedding-based semantic and hybrid retrieval
- [ ] Compare two reports and highlight changes
- [ ] Optional PostgreSQL persistence for saved workspaces
- [ ] Export polished PDF report cards
- [ ] Add evaluation datasets for retrieval quality and answer groundedness

