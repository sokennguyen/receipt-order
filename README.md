# Receipt Order (Textual)

This repository is now initialized with a minimal [Textual](https://textual.textualize.io/) app.

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -e .
   ```

3. Run the app:

   ```bash
   receipt-order
   ```

## Project layout

- `app/main.py`: Textual app entry point.
- `pyproject.toml`: Project metadata, dependencies, and console script.
- `app/data.py`: Canonical dish metadata for display/search/print labels.

## Controls

### Normal mode

- `R` / `G`: enter Ramyun or Gimbap search mode
- `T`: add `Tteokbokki` directly to registered orders
- `D`: delete selected order entry (selection stays at current spot)
- `J` / `K`: move register selection next / previous (wraps)
- `N`: open notes modal for selected register item
- `Ctrl+S`: save current rows to SQLite and print them as one batch
- `Ctrl+C`: no-op
- `Ctrl+Q`: quit app

### Active mode

- Type letters/numbers: build search query
- `Backspace`: delete one query character
- `Tab` / `↑` / `↓`: cycle search results
- `Enter`: register highlighted result into the left order panel
- `Ctrl+C`: exit active mode back to normal mode
- `Ctrl+Q`: quit app
- Search supports shorthand aliases and punctuation-insensitive matching
  - examples: `s-tuna`, `stuna`, and `st` all match `S-Tuna Gimbap`
  - example: `chix` matches `Chicken Ramyun`

### Notes modal

- `J` / `K` / `↑` / `↓`: move note cursor
- `Enter`: toggle highlighted note on/off
- `Esc` / `q` / `Ctrl+C`: close modal

## Persistence / print flow

- SQLite file path: `data/receipt.db`
- Submit (`Ctrl+S`) writes `orders`, `order_items`, and `order_item_notes`
- Print format:
  - mode rows: `<Mode>-<BaseName>` (example: `R-Classic`, `G-Pork`)
  - untagged rows: plain name unless a dish print override exists (example override: `T.T.` for `tteokbokki`)
  - duplicate rows are grouped by mode + dish + exact note set and shown with quantity suffix (example: `R-Classic │3`)
  - groups with notes print one indented line per note under the item line
- If print fails after save, DB records remain (status becomes `PRINT_FAILED`)
