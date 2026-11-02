# Report Explainer

**Make long reports easier to understand.** Upload a PDF or text file, or paste report content, and turn dense writing into a plain-language overview with key findings, important figures, risks, and follow-up questions.

Report Explainer is intentionally small: a polished Python app that demonstrates practical AI integration without unnecessary databases, agents, or infrastructure.

## What it does

- 📄 **PDF and TXT input** — extract selectable PDF text or read text files; paste text directly when convenient.
- 🧠 **AI-powered explanations** — generate an audience-aware explanation using an OpenAI-compatible chat-completions API.
- 🎯 **Choose your audience** — general reader, student, business leader, technical reader, or researcher.
- 🌐 **Multilingual output** — request English, Hindi, Arabic, or Urdu.
- 🔎 **Evidence-aware structure** — summary, findings, important numbers, risks, next steps, and information the source does not provide.
- 📴 **Local fallback** — get a basic, clearly labelled heuristic outline even without an API key.
- ⬇️ **Export results** — download the explanation or outline as Markdown.
- 🧪 **Testable core logic** — text normalization, input validation, and fallback generation are separated into a small utility module.

## Built with

- **Python** — application logic
- **Streamlit** — interactive web interface
- **pypdf** — extract selectable text from PDFs
- **OpenAI Python SDK** — AI provider integration, including compatible endpoints
- **python-dotenv** — local environment configuration
- **pytest** — unit tests and regression checks
- **GitHub Actions** — automated test workflow

## Quick start

### Requirements

- Python 3.11+
- An API key from a supported OpenAI-compatible provider for AI-generated explanations (optional for local outline mode)

### 1. Clone the repository

```bash
git clone https://github.com/Xatreus/report-explainer.git
cd report-explainer
```

### 2. Create and activate a virtual environment

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

### 4. Configure the AI provider (optional)

Copy `.env.example` to `.env`, then set your credentials and model:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o-mini
```

For a compatible provider, use the API base URL and model identifier documented by that provider. Leave `OPENAI_BASE_URL` empty for the default OpenAI endpoint. **Never commit your real API key.** The `.env` file is ignored by Git.

Without a configured key, the app uses its local heuristic outline. That fallback is not an AI summary.

### 5. Launch the app

```bash
streamlit run app.py
```

Streamlit prints a local address (usually `http://localhost:8501`) to open in your browser.

### 6. Run the tests

```bash
pytest -q
```

## How it works

1. **Input:** upload a PDF/TXT file or paste report text.
2. **Extract:** read PDF text locally using `pypdf`; normalize whitespace.
3. **Validate:** reject empty inputs and report text exceeding the 30,000-character processing limit.
4. **Explain:** if AI is configured and enabled, send the extracted text to the selected provider with a structured prompt designed to avoid invented facts.
5. **Export:** review the output and download it as Markdown.

## Project layout

```text
report-explainer/
├── app.py                    # Streamlit UI and AI workflow
├── report_utils.py            # Text extraction, normalization, validation, fallback
├── tests/
│   └── test_report_utils.py   # Unit tests
├── .github/
│   └── workflows/
│       └── tests.yml          # CI test workflow
├── .env.example               # Safe configuration template
├── .gitignore
├── requirements.txt
└── README.md
```

## Privacy and safety

- Files are handled in the current app session; this project does not include an account system or document database.
- When AI mode is used, extracted report text is sent to the configured AI provider. Review that provider's data handling terms before using confidential or personal information.
- The app limits the text sent for explanation and validates input length, but this is a portfolio/demo app—not a hardened document-processing service.
- Report text is untrusted input. The prompt instructs the model to treat embedded instructions as document content, but prompt injection cannot be eliminated by prompting alone.
- AI can omit, misread, or invent claims. Check important figures and conclusions against the original report before making decisions.

## Current limitations

- **Scanned PDFs:** OCR is not included; image-only PDFs may yield no text.
- **Local mode:** uses simple text heuristics and does not understand meaning.
- **Provider compatibility:** custom endpoints must support the chat-completions API expected by the OpenAI SDK.
- **No persistence:** reports and explanations are not saved to a database.

## Roadmap

- [ ] OCR support for scanned reports
- [ ] Downloadable PDF report cards
- [ ] Highlight source passages behind key findings
- [ ] Optional report templates for research, business, and finance
- [ ] Add more tests for PDF extraction and provider failures

## Contributing

Keep the project simple and focused. For changes to text processing, add or update unit tests and run `pytest -q` before opening a pull request.

## License

No license is currently declared. Unless a license is added, standard copyright restrictions apply.
