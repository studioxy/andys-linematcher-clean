# Andy's LineMatcher

Source-only repo for matching `shrep` delivery cities to `rc` destination cities in `colector.xlsx`.

What it does:

- normalizes city names
- matches by country first
- uses fuzzy scoring for spelling variants
- supports manual review in the console
- writes matched results to Excel

## Run

```powershell
python .\match_cities.py .\colector.xlsx -o .\outputs\city_matching.xlsx
```

Or use the console launcher:

```powershell
.\linematcher.cmd
```

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

## Files intentionally not tracked

- input spreadsheets
- generated output spreadsheets
- `build/`
- `dist/`
- cache and bytecode files
