# AI Accountant - Smart Diff Checker

## Overview

AI Accountant is a smart document comparison tool designed to analyze invoice and accounting documents. It uses OpenAI's vision capabilities to identify differences between multiple versions of documents and generates detailed explanations of those differences. The app streamlines the reconciliation process by automatically comparing invoices, detecting discrepancies, and helping draft clarification emails based on identified variations.

## Features

- **Multi-document comparison**: Upload and compare up to three documents side-by-side
- **AI-powered difference detection**: Uses OpenAI to intelligently identify and explain discrepancies
- **Multimodal input support**: Handles PDFs, scanned documents, and photographs equally well
- **Structured explanations**: Generates a detailed table of findings
- **Email drafting**: Automatically creates professional emails to communicate discrepancies

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

## Run

```bash
uv run streamlit run app.py
```

## Notes

- Supported upload formats: PDF, PNG, JPG/JPEG (including photos or screenshots of documents).
- Files are sent directly to the model as multimodal input (no local text extraction), so
  scanned or photographed documents are handled the same way as native PDFs.
- The "Find Differences" step sends the three documents to OpenAI and expects a JSON array
  back, which is parsed into the Explanations table.
- The "Generate Email" step drafts an email from the current Explanations table and the
  instructions box.
- `MODEL` in `app.py` defaults to `gpt-5.6` — update it if you'd rather use a different
  OpenAI model.
- Dependencies are managed with `uv` (`pyproject.toml` + `uv.lock`). `exclude-newer` in
  `[tool.uv]` pins resolution to packages published on or before that date for reproducibility.
