# AI Accountant - Smart Diff Checker

## Setup

```bash
uv sync
```

Set your OpenAI API key, either as an environment variable:

```bash
export OPENAI_API_KEY=sk-...
```

or in `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "sk-..."
```

The app is gated behind a shared secret. Set `USER_PWD` alongside `OPENAI_API_KEY` (env var
or `secrets.toml`) — visitors must enter it to reach the app.

## Run

```bash
uv run streamlit run streamlit_app.py
```

## Notes

- Supported upload formats: PDF, PNG, JPG/JPEG (including photos or screenshots of documents).
- Files are sent directly to the model as multimodal input (no local text extraction), so
  scanned or photographed documents are handled the same way as native PDFs.
- The "Find Differences" step sends the three documents to OpenAI and expects a markdown
  table back matching the Explanations columns, which is parsed into the Explanations table.
- The "Generate Email" step drafts an email from the current Explanations table and the
  instructions box.
- `MODEL` in `streamlit_app.py` defaults to `gpt-5.6-terra` — a balanced choice for document
  comparison. Bump to `gpt-5.6-sol` for denser or trickier documents where missed discrepancies
  are costly; `gpt-5.6-luna` is cheaper but not recommended here, as it's tuned for high-volume/
  classification tasks rather than careful multi-document reconciliation.
- Dependencies are managed with `uv` (`pyproject.toml` + `uv.lock`). `exclude-newer` in
  `[tool.uv]` pins resolution to packages published on or before that date for reproducibility.