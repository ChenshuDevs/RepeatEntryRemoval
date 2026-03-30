# Repeat Row Remover

A Streamlit web app that uploads CSV or Excel files, removes repeated rows by comparing row values, and shows before/after treatment metrics and previews.

## Features

- Upload `.csv`, `.xlsx`, or `.xls`
- Remove duplicate rows regardless of column names
- Keep the first occurrence of each repeated row
- Visualize row counts before and after cleanup
- Download the cleaned file after processing

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Streamlit Community Cloud deployment

1. Push this project to GitHub.
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Sign in with GitHub.
4. Click `Create app`.
5. Select your repository and branch.
6. Set the main file path to `app.py`.
7. Click `Deploy`.

## Notes

- `.xls` uploads are supported for reading and exported as `.xlsx` after cleanup.
- Duplicate detection compares the full row values in order and ignores the meaning of column names.
