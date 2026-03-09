# UNSC Resolution Metadata Manager

A Streamlit-based tool for registering, editing, and exporting UN Security Council resolution metadata as structured JSON.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Python 3.11+ required. Opens at `http://localhost:8501`.

## Usage

Click the **Help** button in the app for a full bilingual usage guide (Japanese / English).

The app has three views:

- **✏️ Edit** — Register new records or modify existing ones
- **📋 List** — Browse, search, sort, and view record details
- **Help** — Step-by-step instructions for every operation

## Design Highlights

- **Minimal required input** — Only 4 fields needed to save: URL, Resolution number, Date, Title. Everything else is optional.
- **Inline field help** — Every field shows its expected format via tooltip (e.g. `YYYYMMDD`, `Integer`). Required fields are marked with `*`.
- **Safe by design** — No delete button in the UI. Deletion requires an administrator to directly edit `data/records.json`. This prevents accidental data loss.
- **Auto timestamps** — `created_at` and `updated_at` are recorded automatically on every save.
- **Sortable list** — Sort by last updated, resolution number, or date (ascending/descending).
- **Pagination** — 50 records per page with navigation buttons at both top and bottom.
- **Expandable detail view** — Click "View" on any row to see a formatted breakdown without leaving the list. Close buttons at top and bottom.
- **One-click export** — "Download public JSON" auto-regenerates and downloads directly from the browser.
- **Bilingual help** — Japanese (left) and English (right) side-by-side in the Help view.
- **Red delete buttons** — Block removal buttons are red and right-aligned, separated from Save to prevent misclicks.
- **Cancel support** — Discard edits anytime with the Cancel button.

## Data Files

| File | Description |
|---|---|
| `data/records.json` | Internal full records (source of truth) |
| `data/public_records.json` | Public-facing export (auto-generated from records.json) |

## File Structure

```
app.py                # Streamlit UI (3-view: Edit / List / Help)
form_spec.py          # Form structure, defaults, category labels
masters.py            # Option lists derived from Excel specification
validators.py         # Validation, normalization, timestamp generation
storage.py            # JSON read/write
export_public.py      # Public JSON generation
data/
  records.json        # Internal records (source of truth)
  public_records.json # Public export (hand to frontend)
```

## Deployment Workflow

1. Register/edit records in the app
2. Click **Download public JSON** on the List view
3. Hand `public_records.json` to the frontend maintainer
4. Frontend maintainer places the file in the repository and deploys

## Pinned Versions

- Python: 3.11+ (`.python-version`)
- Streamlit: 1.39.0 (`requirements.txt`)

## License

MIT License (c) 2026 Jin Nakamura
