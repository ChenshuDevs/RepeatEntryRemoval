# Repeat Row Remover

A Flask web app for Render that uploads CSV or Excel files, removes repeated rows by comparing row values, and shows before/after treatment metrics and previews.

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
python app.py
```

Open `http://127.0.0.1:5000`.

## Render deployment

1. Push this project to GitHub.
2. Create a new Render Web Service from the repo.
3. Render will detect [`render.yaml`](/Users/chenshudevs/Documents/Repeat_entry_removal/render.yaml).
4. Deploy the service.

## Notes

- `.xls` uploads are supported for reading and exported as `.xlsx` after cleanup.
- Duplicate detection compares the full row values in order and ignores the meaning of column names.
# RepeatEntryRemoval
