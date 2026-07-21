import base64
import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI

from diff_prompt import DIFF_PROMPT
from email_prompt import EMAIL_PROMPT

MODEL = "gpt-5.6"

COLUMNS = [
    "Good / Service",
    "Value at Invoice",
    "Value at Reference",
    "Difference",
    "Root Cause",
    "Comments",
    "Severity",
]

# Maps normalized (lowercased, alnum-only) key variants -> the canonical column name,
# so the app works whether DIFF_PROMPT asks the model for snake_case or Title Case keys.
COLUMN_ALIASES = {
    "goodservice": "Good / Service",
    "good": "Good / Service",
    "valueatinvoice": "Value at Invoice",
    "valueatreference": "Value at Reference",
    "difference": "Difference",
    "rootcause": "Root Cause",
    "comments": "Comments",
    "severity": "Severity",
}

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

st.set_page_config(page_title="AI Accountant - Smart Diff Checker", layout="wide")


def file_to_content_block(uploaded_file) -> dict:
    """Turn an uploaded PDF/PNG/JPG into an OpenAI multimodal content block."""
    suffix = Path(uploaded_file.name).suffix.lower()
    mime = MIME_TYPES[suffix]
    data = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

    if suffix == ".pdf":
        return {
            "type": "file",
            "file": {"filename": uploaded_file.name, "file_data": f"data:{mime};base64,{data}"},
        }

    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}


def get_client() -> OpenAI:
    api_key = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))
    if not api_key:
        st.error("Set OPENAI_API_KEY in st.secrets or your environment.")
        st.stop()
    return OpenAI(api_key=api_key)


def parse_markdown_table(raw: str) -> pd.DataFrame:
    """Parse a markdown table (optionally fenced) into a DataFrame."""
    raw = re.sub(r"^```(?:markdown)?", "", raw.strip()).strip()
    raw = re.sub(r"```$", "", raw).strip()

    lines = [l for l in raw.splitlines() if l.strip().startswith("|")]
    if len(lines) < 2:
        raise ValueError("No markdown table found in the model output.")

    def split_row(line: str) -> list:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    header = split_row(lines[0])
    data_rows = [row for row in (split_row(l) for l in lines[2:] if l.strip()) if len(row) == len(header)]
    return pd.DataFrame(data_rows, columns=header)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    def norm(col: str) -> str:
        key = re.sub(r"[^a-z0-9]", "", col.lower())
        return COLUMN_ALIASES.get(key, col)

    return df.rename(columns={c: norm(c) for c in df.columns})


def find_differences(invoice_file, reference_file, contract_file) -> pd.DataFrame:
    content = [{"type": "text", "text": DIFF_PROMPT}]
    for label, uploaded_file in (
        ("INVOICE:", invoice_file),
        ("REFERENCE:", reference_file),
        ("CONTRACT:", contract_file),
    ):
        content.append({"type": "text", "text": label})
        content.append(file_to_content_block(uploaded_file))

    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": content}],
        max_completion_tokens=8000,
        reasoning_effort="low",
    )
    choice = response.choices[0]
    raw = (choice.message.content or "").strip()

    if not raw:
        st.error(
            f"The model returned no visible content (finish_reason={choice.finish_reason!r}). "
            "This usually means the reasoning budget used up max_completion_tokens before any "
            "output was written — try raising max_completion_tokens."
        )
        st.stop()

    try:
        df = parse_markdown_table(raw)
    except ValueError:
        st.error("Could not parse the model's response as a markdown table. Raw response below:")
        st.code(raw)
        st.stop()

    df = normalize_columns(df)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        st.error(f"Model output is missing expected columns: {missing}")
        st.code(raw)
        st.stop()

    return df[COLUMNS]


def generate_email(explanations_df: pd.DataFrame, instructions: str) -> str:
    prompt = EMAIL_PROMPT.format(
        instructions=instructions, explanations=explanations_df.to_markdown(index=False)
    )

    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=2000,
        reasoning_effort="low",
    )
    choice = response.choices[0]
    text = (choice.message.content or "").strip()
    if not text:
        st.error(
            f"The model returned no visible content (finish_reason={choice.finish_reason!r}). "
            "Try raising max_completion_tokens."
        )
        st.stop()
    return text


def empty_table_markdown() -> str:
    header = "| " + " | ".join(COLUMNS) + " |"
    divider = "|" + "|".join(["-" * (len(c) + 2) for c in COLUMNS]) + "|"
    return f"{header}\n{divider}"


if "explanations_df" not in st.session_state:
    st.session_state.explanations_df = pd.DataFrame(columns=COLUMNS)
if "email_output" not in st.session_state:
    st.session_state["email_output"] = ""

st.title("AI Accountant - Smart Diff Checker")
st.write(
    "Input your invoice, reference and contract and get a detailed description of the "
    "differences observed."
)

st.header("Inputs")
col1, col2, col3 = st.columns(3)
with col1:
    invoice_file = st.file_uploader("Invoice", type=["pdf", "png", "jpg", "jpeg"])
with col2:
    reference_file = st.file_uploader("Reference", type=["pdf", "png", "jpg", "jpeg"])
with col3:
    contract_file = st.file_uploader("Contract", type=["pdf", "png", "jpg", "jpeg"])

if st.button("Find Differences", type="primary"):
    if not (invoice_file and reference_file and contract_file):
        st.warning("Please upload all three documents before running.")
    else:
        with st.spinner("Comparing documents..."):
            st.session_state.explanations_df = find_differences(
                invoice_file, reference_file, contract_file
            )

st.header("Explanations")
if st.session_state.explanations_df.empty:
    st.markdown(empty_table_markdown())
else:
    st.markdown(st.session_state.explanations_df.to_markdown(index=False))

st.header("Email")
instructions = st.text_area(
    "Instructions", value="Use only explanation 1", key="email_instructions"
)

if st.button("Generate Email"):
    if st.session_state.explanations_df.empty:
        st.warning("Run 'Find Differences' first.")
    else:
        with st.spinner("Drafting email..."):
            st.session_state["email_output"] = generate_email(
                st.session_state.explanations_df, instructions
            )

st.text_area("Generated Email", height=250, key="email_output")