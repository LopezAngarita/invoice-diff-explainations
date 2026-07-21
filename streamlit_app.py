import base64
import io
import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI
from PIL import Image
from streamlit_paste_button import paste_image_button as pbutton

from diff_prompt import DIFF_PROMPT
from email_prompt import EMAIL_PROMPT

MODEL = "gpt-5.6-terra"

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


def file_to_content_block(source) -> dict:
    """Turn an uploaded PDF/PNG/JPG or a pasted PIL image into an OpenAI multimodal content block."""
    if isinstance(source, Image.Image):
        buf = io.BytesIO()
        source.save(buf, format="PNG")
        data = base64.b64encode(buf.getvalue()).decode("utf-8")
        return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}}

    suffix = Path(source.name).suffix.lower()
    mime = MIME_TYPES[suffix]
    data = base64.b64encode(source.getvalue()).decode("utf-8")

    if suffix == ".pdf":
        return {
            "type": "file",
            "file": {"filename": source.name, "file_data": f"data:{mime};base64,{data}"},
        }

    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}


def resolve_input(uploaded_file, paste_result):
    """Prefer an uploaded file; fall back to a pasted image; else None."""
    if uploaded_file is not None:
        return uploaded_file
    if paste_result.image_data is not None:
        return paste_result.image_data
    return None


def get_client() -> OpenAI:
    api_key = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))
    if not api_key:
        st.error("Set OPENAI_API_KEY in st.secrets or your environment.")
        st.stop()
    return OpenAI(api_key=api_key)


def parse_markdown_table(raw: str) -> pd.DataFrame:
    """Parse a markdown table (optionally fenced, possibly with stray text around it)."""
    raw = re.sub(r"^```(?:markdown)?", "", raw.strip()).strip()
    raw = re.sub(r"```$", "", raw).strip()

    table_lines = [l for l in raw.splitlines() if l.strip().startswith("|")]
    if len(table_lines) < 2:
        raise ValueError("No markdown table found in the model output.")

    df = pd.read_csv(io.StringIO("\n".join(table_lines)), sep="|", skipinitialspace=True)
    df = df.dropna(axis=1, how="all")
    df = df.iloc[1:].reset_index(drop=True)  # drop the |---|---| separator row
    df.columns = df.columns.str.strip()
    return df.map(lambda x: x.strip() if isinstance(x, str) else x)


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


def check_password() -> bool:
    """Gate the app behind the shared secret in st.secrets['USER_PWD']."""
    if st.session_state.get("authenticated"):
        return True

    st.title("AI Accountant - Smart Diff Checker")
    secret = st.text_input("Secret", type="password", key="secret_input")
    if st.button("Enter"):
        if secret == st.secrets.get("USER_PWD"):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Wrong secret.")
    return False


def empty_table_markdown() -> str:
    header = "| " + " | ".join(COLUMNS) + " |"
    divider = "|" + "|".join(["-" * (len(c) + 2) for c in COLUMNS]) + "|"
    return f"{header}\n{divider}"


if "explanations_df" not in st.session_state:
    st.session_state.explanations_df = pd.DataFrame(columns=COLUMNS)
if "email_output" not in st.session_state:
    st.session_state["email_output"] = ""

if not check_password():
    st.stop()

st.title("AI Accountant - Smart Diff Checker")
st.write(
    "Input your invoice, reference and contract and get a detailed description of the "
    "differences observed."
)

if "input_version" not in st.session_state:
    st.session_state.input_version = 0

st.header("Inputs")
v = st.session_state.input_version
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Invoice**")
    invoice_upload = st.file_uploader(
        "Invoice",
        type=["pdf", "png", "jpg", "jpeg"],
        key=f"invoice_uploader_{v}",
        label_visibility="collapsed",
    )
    invoice_paste = pbutton("📋 Paste from clipboard", key=f"invoice_paste_{v}")
    invoice_file = resolve_input(invoice_upload, invoice_paste)
    if invoice_paste.image_data is not None:
        st.image(invoice_paste.image_data, caption="Pasted", width=120)

with col2:
    st.markdown("**Reference**")
    reference_upload = st.file_uploader(
        "Reference",
        type=["pdf", "png", "jpg", "jpeg"],
        key=f"reference_uploader_{v}",
        label_visibility="collapsed",
    )
    reference_paste = pbutton("📋 Paste from clipboard", key=f"reference_paste_{v}")
    reference_file = resolve_input(reference_upload, reference_paste)
    if reference_paste.image_data is not None:
        st.image(reference_paste.image_data, caption="Pasted", width=120)

with col3:
    st.markdown("**Contract**")
    contract_upload = st.file_uploader(
        "Contract",
        type=["pdf", "png", "jpg", "jpeg"],
        key=f"contract_uploader_{v}",
        label_visibility="collapsed",
    )
    contract_paste = pbutton("📋 Paste from clipboard", key=f"contract_paste_{v}")
    contract_file = resolve_input(contract_upload, contract_paste)
    if contract_paste.image_data is not None:
        st.image(contract_paste.image_data, caption="Pasted", width=120)

run_col, reset_col = st.columns([1, 1])
with run_col:
    run_clicked = st.button("Find Differences", type="primary")
with reset_col:
    if st.button("Reset Inputs"):
        st.session_state.input_version += 1
        st.rerun()

if run_clicked:
    if not (invoice_file and reference_file and contract_file):
        st.warning("Please upload or paste all three documents before running.")
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