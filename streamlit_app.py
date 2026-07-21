import base64
import json
import os
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


def find_differences(invoice_file, reference_file, contract_file) -> pd.DataFrame:
    instructions = DIFF_PROMPT
    content = [{"type": "text", "text": instructions}]
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
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    rows = json.loads(raw)

    df = pd.DataFrame(rows)
    # df = df.rename(
    #     columns={
    #         "good_service": "Good / Service",
    #         "value_at_invoice": "Value at Invoice",
    #         "value_at_reference": "Value at Reference",
    #         "difference": "Difference",
    #         "root_cause": "Root Cause",
    #         "comments": "Comments",
    #         "severity": "Severity",
    #     }
    )
    return df[COLUMNS]


def generate_email(explanations_df: pd.DataFrame, instructions: str) -> str:
    prompt = EMAIL_PROMPT.format(instructions=instructions, 
    explanations=explanations_df.to_markdown(index=False))

    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def empty_table_markdown() -> str:
    header = "| " + " | ".join(COLUMNS) + " |"
    divider = "|" + "|".join(["-" * (len(c) + 2) for c in COLUMNS]) + "|"
    return f"{header}\n{divider}"


if "explanations_df" not in st.session_state:
    st.session_state.explanations_df = pd.DataFrame(columns=COLUMNS)
if "email_text" not in st.session_state:
    st.session_state.email_text = ""

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
            st.session_state.email_text = generate_email(
                st.session_state.explanations_df, instructions
            )

st.text_area("Generated Email", value=st.session_state.email_text, height=250, key="email_output")
