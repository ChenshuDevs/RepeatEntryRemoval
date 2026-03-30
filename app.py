import os
import uuid
from collections import Counter
from datetime import datetime

import pandas as pd
from flask import Flask, render_template, request, send_from_directory
from werkzeug.utils import secure_filename


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PROCESSED_FOLDER = os.path.join(BASE_DIR, "processed")
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
MAX_CONTENT_LENGTH = 25 * 1024 * 1024


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROCESSED_FOLDER"] = PROCESSED_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


for folder in (UPLOAD_FOLDER, PROCESSED_FOLDER):
    os.makedirs(folder, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_cell(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_dataframe(file_path: str) -> pd.DataFrame:
    extension = file_path.rsplit(".", 1)[1].lower()
    if extension == "csv":
        return pd.read_csv(file_path, dtype=object, keep_default_na=True)
    if extension == "xlsx":
        return pd.read_excel(file_path, dtype=object, engine="openpyxl")
    if extension == "xls":
        return pd.read_excel(file_path, dtype=object, engine="xlrd")
    raise ValueError("Unsupported file type.")


def build_duplicate_groups(normalized_df: pd.DataFrame, original_df: pd.DataFrame, limit: int = 5):
    row_signatures = [tuple(row) for row in normalized_df.itertuples(index=False, name=None)]
    counts = Counter(row_signatures)

    groups = []
    seen = set()
    for signature, count in counts.most_common():
        if count <= 1 or signature in seen:
            continue
        match_index = next(
            idx for idx, row in enumerate(normalized_df.itertuples(index=False, name=None)) if tuple(row) == signature
        )
        sample_values = original_df.iloc[match_index].fillna("").astype(str).tolist()
        groups.append(
            {
                "count": count,
                "values": sample_values,
            }
        )
        seen.add(signature)
        if len(groups) >= limit:
            break
    return groups


def process_dataframe(df: pd.DataFrame):
    original_df = df.copy()
    normalized_df = df.applymap(normalize_cell)
    duplicate_mask = normalized_df.duplicated(keep="first")
    cleaned_df = original_df.loc[~duplicate_mask].copy()

    original_rows = len(original_df)
    cleaned_rows = len(cleaned_df)
    removed_rows = int(duplicate_mask.sum())
    duplicate_rate = round((removed_rows / original_rows) * 100, 2) if original_rows else 0

    chart_data = {
        "labels": ["Before cleanup", "After cleanup"],
        "rowCounts": [original_rows, cleaned_rows],
        "distribution": [cleaned_rows, removed_rows],
    }

    summary = {
        "original_rows": original_rows,
        "cleaned_rows": cleaned_rows,
        "removed_rows": removed_rows,
        "duplicate_rate": duplicate_rate,
        "columns": list(original_df.columns),
        "before_preview": original_df.head(10).fillna("").astype(str).to_dict(orient="records"),
        "after_preview": cleaned_df.head(10).fillna("").astype(str).to_dict(orient="records"),
        "top_duplicate_groups": build_duplicate_groups(normalized_df, original_df),
        "chart_data": chart_data,
    }

    return cleaned_df, summary


def save_cleaned_file(cleaned_df: pd.DataFrame, original_name: str):
    stem, extension = os.path.splitext(original_name)
    extension = extension.lower()
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    token = uuid.uuid4().hex[:8]

    if extension == ".csv":
        output_name = f"{stem}_deduplicated_{timestamp}_{token}.csv"
        output_path = os.path.join(PROCESSED_FOLDER, output_name)
        cleaned_df.to_csv(output_path, index=False)
    else:
        output_name = f"{stem}_deduplicated_{timestamp}_{token}.xlsx"
        output_path = os.path.join(PROCESSED_FOLDER, output_name)
        cleaned_df.to_excel(output_path, index=False, engine="openpyxl")

    return output_name


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_file():
    uploaded_file = request.files.get("data_file")
    if not uploaded_file or uploaded_file.filename == "":
        return render_template("index.html", error="Please upload a CSV or Excel file.")

    if not allowed_file(uploaded_file.filename):
        return render_template("index.html", error="Unsupported file type. Use CSV, XLSX, or XLS.")

    safe_name = secure_filename(uploaded_file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    upload_path = os.path.join(UPLOAD_FOLDER, unique_name)
    uploaded_file.save(upload_path)

    try:
        dataframe = read_dataframe(upload_path)
        cleaned_df, summary = process_dataframe(dataframe)
        download_name = save_cleaned_file(cleaned_df, safe_name)
    except Exception as exc:
        return render_template(
            "index.html",
            error=f"Could not process the file. Please verify the format and contents. Details: {exc}",
        )

    notice = None
    if safe_name.lower().endswith(".xls"):
        notice = "Legacy .xls uploads are exported as .xlsx after cleanup for better compatibility."

    return render_template(
        "index.html",
        success="File processed successfully.",
        notice=notice,
        filename=safe_name,
        summary=summary,
        download_name=download_name,
    )


@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename: str):
    return send_from_directory(app.config["PROCESSED_FOLDER"], filename, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
