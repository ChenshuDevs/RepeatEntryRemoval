from collections import Counter
from io import BytesIO

import pandas as pd
import streamlit as st


ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


def normalize_cell(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_dataframe(uploaded_file) -> pd.DataFrame:
    extension = uploaded_file.name.rsplit(".", 1)[1].lower()
    uploaded_file.seek(0)
    if extension == "csv":
        return pd.read_csv(uploaded_file, dtype=object, keep_default_na=True)
    if extension == "xlsx":
        return pd.read_excel(uploaded_file, dtype=object, engine="openpyxl")
    if extension == "xls":
        return pd.read_excel(uploaded_file, dtype=object, engine="xlrd")
    raise ValueError("Unsupported file type.")


def build_duplicate_groups(normalized_df: pd.DataFrame, original_df: pd.DataFrame, limit: int = 5):
    row_signatures = [tuple(row) for row in normalized_df.itertuples(index=False, name=None)]
    counts = Counter(row_signatures)

    groups = []
    for signature, count in counts.most_common():
        if count <= 1:
            continue

        match_index = next(
            idx for idx, row in enumerate(normalized_df.itertuples(index=False, name=None)) if tuple(row) == signature
        )
        sample_values = original_df.iloc[match_index].fillna("").astype(str).tolist()
        groups.append({"count": count, "values": sample_values})

        if len(groups) >= limit:
            break

    return groups


def process_dataframe(df: pd.DataFrame):
    original_df = df.copy()
    normalized_df = df.map(normalize_cell)
    duplicate_mask = normalized_df.duplicated(keep="first")
    cleaned_df = original_df.loc[~duplicate_mask].copy()

    original_rows = len(original_df)
    cleaned_rows = len(cleaned_df)
    removed_rows = int(duplicate_mask.sum())
    duplicate_rate = round((removed_rows / original_rows) * 100, 2) if original_rows else 0.0

    summary = {
        "original_rows": original_rows,
        "cleaned_rows": cleaned_rows,
        "removed_rows": removed_rows,
        "duplicate_rate": duplicate_rate,
        "columns": list(original_df.columns),
        "before_preview": original_df.head(10).fillna("").astype(str),
        "after_preview": cleaned_df.head(10).fillna("").astype(str),
        "top_duplicate_groups": build_duplicate_groups(normalized_df, original_df),
    }
    return cleaned_df, summary


def make_download_payload(cleaned_df: pd.DataFrame, original_name: str):
    stem, extension = original_name.rsplit(".", 1)
    extension = extension.lower()

    if extension == "csv":
        data = cleaned_df.to_csv(index=False).encode("utf-8")
        return {
            "file_name": f"{stem}_deduplicated.csv",
            "mime": "text/csv",
            "data": data,
        }

    output = BytesIO()
    cleaned_df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    return {
        "file_name": f"{stem}_deduplicated.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "data": output.getvalue(),
    }


st.set_page_config(
    page_title="Repeat Row Remover",
    page_icon=":bar_chart:",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(240,138,36,0.18), transparent 28%),
            radial-gradient(circle at right center, rgba(20,99,86,0.16), transparent 24%),
            linear-gradient(180deg, #f7efe4 0%, #fbf7f0 100%);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .hero {
        padding: 2rem 2.2rem;
        border-radius: 26px;
        background: rgba(255, 251, 245, 0.85);
        border: 1px solid rgba(39,45,39,0.10);
        box-shadow: 0 24px 60px rgba(51,35,18,0.10);
        margin-bottom: 1.25rem;
    }
    .hero h1 {
        margin: 0;
        color: #1f241f;
    }
    .hero p {
        margin: 0.75rem 0 0;
        color: #566156;
        font-size: 1.05rem;
        line-height: 1.6;
        max-width: 56rem;
    }
    .metric-box {
        padding: 1rem 1.1rem;
        border-radius: 18px;
        background: rgba(255, 251, 245, 0.84);
        border: 1px solid rgba(39,45,39,0.10);
    }
    .dup-box {
        padding: 0.9rem 1rem;
        border-radius: 16px;
        background: rgba(20,99,86,0.06);
        border: 1px solid rgba(20,99,86,0.12);
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>Remove repeated rows from CSV and Excel files</h1>
        <p>
            Upload a dataset, detect repeated rows by comparing the full row values, keep the first occurrence,
            and review before-and-after treatment results with charts, metrics, and previews.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a CSV, XLSX, or XLS file",
    type=sorted(ALLOWED_EXTENSIONS),
    help="Duplicate detection compares entire row values in order rather than depending on the column names.",
)

if uploaded_file is None:
    st.info("Upload a file to start the cleanup workflow.")
    st.stop()

try:
    dataframe = read_dataframe(uploaded_file)
    cleaned_df, summary = process_dataframe(dataframe)
    download_payload = make_download_payload(cleaned_df, uploaded_file.name)
except Exception as exc:
    st.error(f"Could not process this file. Please verify the format and contents. Details: {exc}")
    st.stop()

if uploaded_file.name.lower().endswith(".xls"):
    st.warning("Legacy .xls files are exported as .xlsx after cleanup for better compatibility.")

st.success("File processed successfully.")

metric_columns = st.columns(4)
metric_columns[0].metric("Rows before", summary["original_rows"])
metric_columns[1].metric("Rows after", summary["cleaned_rows"])
metric_columns[2].metric("Duplicates removed", summary["removed_rows"])
metric_columns[3].metric("Duplicate rate", f"{summary['duplicate_rate']}%")

chart_left, chart_right = st.columns(2)

with chart_left:
    st.subheader("Row count comparison")
    comparison_df = pd.DataFrame(
        {
            "Stage": ["Before cleanup", "After cleanup"],
            "Rows": [summary["original_rows"], summary["cleaned_rows"]],
        }
    ).set_index("Stage")
    st.bar_chart(comparison_df)

with chart_right:
    st.subheader("Cleanup distribution")
    distribution_df = pd.DataFrame(
        {
            "Category": ["Rows kept", "Rows removed"],
            "Count": [summary["cleaned_rows"], summary["removed_rows"]],
        }
    ).set_index("Category")
    st.bar_chart(distribution_df)

preview_left, preview_right = st.columns(2)

with preview_left:
    st.subheader("Before treatment")
    st.dataframe(summary["before_preview"], use_container_width=True)

with preview_right:
    st.subheader("After treatment")
    st.dataframe(summary["after_preview"], use_container_width=True)

st.subheader("Most repeated row patterns")
if summary["top_duplicate_groups"]:
    for group in summary["top_duplicate_groups"]:
        values_text = " | ".join(group["values"]) if group["values"] else "(empty row)"
        st.markdown(
            f"""
            <div class="dup-box">
                <strong>{group["count"]} matches</strong><br>
                <span>{values_text}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.info("No duplicate row groups were found in this file.")

st.download_button(
    label="Download cleaned file",
    data=download_payload["data"],
    file_name=download_payload["file_name"],
    mime=download_payload["mime"],
    use_container_width=True,
)
