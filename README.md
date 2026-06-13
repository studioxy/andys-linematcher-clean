# Andy's LineMatcher

Source-only repo for matching `shrep` delivery cities to `rc` destination cities in `colector.xlsx`.

What it does:

- normalizes city names
- matches by country first
- uses fuzzy scoring for spelling variants
- supports manual review in the console
- writes matched results to Excel

## Matching stack

Detailed algorithm notes are included in:

- [docs/MATCHING_STACK.md](docs/MATCHING_STACK.md)
- `docs/MATCHING_STACK.pdf`
- [docs/MATCHING_STACK_PL.md](docs/MATCHING_STACK_PL.md)
- `docs/MATCHING_STACK_PL.pdf`

The document explains:

- normalization and country filtering
- alias override behavior
- the exact fuzzy scoring functions
- thresholds, margins, and review routing
- why this is deterministic fuzzy matching rather than ML

To rebuild the PDF:

```powershell
python .\scripts\build_matching_stack_pdf.py
```

To rebuild only the Polish version:

```powershell
python .\scripts\build_matching_stack_pdf.py --lang pl
```

This requires `reportlab`. The tracked PDFs in `docs/` are already ready to use.

## Run

```powershell
python .\match_cities.py .\colector.xlsx -o .\outputs\city_matching.xlsx
```

Or use the console launcher:

```powershell
.\linematcher.cmd
```

When started without an explicit workbook path, the launcher:

- first looks for the configured filename from `linematcher.config.json`
- otherwise uses the only `.xlsx` file in the launcher folder
- if several `.xlsx` files exist, asks you which one to open

Manual review mode:

```powershell
.\linematcher-review.cmd
```

The app can also be run as a standalone Windows executable:

```powershell
.\dist\linematcher.exe .\colector.xlsx -o .\outputs\city_matching.xlsx
```

When run with no arguments, it looks for `colector.xlsx` in the current folder,
asks whether to enter review, and waits for Enter before closing the console.

## Output

- `summary` - counts and thresholds
- `city_map` - unique city-country pairs with match decisions
- `matched_rows` - row-level results with RC fields attached
- `review_needed` - unresolved rows for manual review
- `suggested_aliases` - accepted mappings that can be added to `city_aliases.csv`

## Statuses

- `auto_matched`
- `manual_matched`
- `review_needed`
- `unmatched`

## Build

```powershell
.\build_exe.cmd
```

## Config

The repo includes:

- [linematcher.config.json](linematcher.config.json)

It controls:

- default input workbook filename
- worksheet names for `rc` and `shrep`
- required city/country column names for both sheets

## Files intentionally not tracked

- input spreadsheets
- generated output spreadsheets
- `build/`
- `dist/`
- cache and bytecode files
