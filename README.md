# Repeat Row Remover

A static HTML/CSS/JavaScript web app that uploads CSV or Excel files, removes repeated rows by comparing row values, and shows before/after treatment metrics and previews.

## Features

- Upload `.csv`, `.xlsx`, or `.xls`
- Remove duplicate rows regardless of column names
- Keep the first occurrence of each repeated row
- Visualize row counts before and after cleanup
- Download the cleaned file after processing
- Run entirely in the browser with no backend required

## Local run

Open [index.html](/Users/chenshudevs/Documents/Repeat_entry_removal/index.html) directly in a browser, or serve the folder with any static server.

Example:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Static deployment

You can deploy this on any static host such as GitHub Pages, Netlify, Vercel static hosting, Cloudflare Pages, or an S3 bucket.

1. Push this project to GitHub.
2. Create a new static site on your preferred host.
3. Set the publish directory to the project root.
4. Deploy.

## Notes

- `.xls` uploads are supported for reading and exported as `.xlsx` after cleanup.
- Duplicate detection compares the full row values in order and ignores the meaning of column names.
- CSV parsing uses Papa Parse and Excel parsing/export uses SheetJS in the browser.
