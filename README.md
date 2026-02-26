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

- `R` / `G` / `S`: enter Ramyun, Gimbap, or Side Dish search mode
- `T`: add `Tteokbokki` directly to registered orders
- `D`: delete selected order entry (selection stays at current spot)
- `J` / `K`: move register selection next / previous (wraps)
- `Shift+J` / `Shift+K`: reorder selected item/group down / up; in View mode, reorder selected range block (no wrap)
- `V`: enter register View mode (range highlight); `J/K` adjusts range, `gg` jumps to first row, `G` jumps to last row, `Esc/q/Ctrl+C` exits
- `Shift+V`: reserved for future linewise View mode (not implemented yet)
- `C`: group selected register row(s) into one customer group (view-range or single row)
- `Shift+C`: ungroup selected customer group row
- `a`: toggle takeaway tag on current selection (single row/member, group header members, or current view selection)
- `Shift+A`: toggle takeaway for whole order (`all takeaway -> clear all`, otherwise set all takeaway)
- `N`: open notes modal for selected register item
- `Ctrl+S`: open Order Number modal (0..1000), then save + print on confirm
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
  - Side Dish mode items: `Kimchi`, `Ssamjang`, `Namu`, `Hot`, `Rice`

### Notes modal

- `J` / `K` / `↑` / `↓`: move note cursor
- `Enter`: toggle highlighted note on/off
- `Other note` row is always at the bottom:
  - `Enter` on `Other note` starts inline typing (`Other note: ...|`)
  - while typing: printable keys insert text, `Backspace` deletes, `Enter` confirms, `Esc` cancels typing
  - confirmed text is added as a selected custom note row above `Other note`
  - custom rows can be toggled off (removed/discarded)
- `Esc` / `q` / `Ctrl+C`: close modal

### Order Number modal

- digits: enter order number (`0..1000`)
- `Ctrl+N`: toggle runtime `NOT PAID` marker for this ticket header
- `Enter`: confirm
- `Esc` / `q` / `Ctrl+C`: cancel submit

## Persistence / print flow

- SQLite file path: `data/receipt.db`
- Submit (`Ctrl+S`) prompts for order number (0..1000); cancel aborts submit
- In order-number modal, `Ctrl+N` toggles a runtime `NOT PAID` marker printed in the header (not persisted)
- Confirmed submit writes `orders` (including `order_number`), `order_items`, and `order_item_notes`
- Selected custom `Other note` entries are saved in `order_item_notes` using `note_id` like `custom:{index}` and `note_label` text
- Print format:
  - header behavior:
    - `order_number > 0`: prints right-aligned order number (plus `NOT PAID` if toggled)
    - `order_number == 0` and paid: no header printed
    - `order_number == 0` and `NOT PAID`: prints header with small `NOT PAID` marker only
  - mode rows: `<Mode>-<BaseName>` (example: `R-Classic`, `G-Pork`)
  - untagged rows: plain name unless a dish print override exists (example override: `T.T.` for `tteokbokki`)
  - duplicate rows are grouped by mode + dish + exact note set and shown with quantity suffix (example: `R-Classic │3`)
  - duplicate rows with manually grouped members include one compact allocation line (example: `1 2x2`)
  - groups with notes print one indented line per note under the item line
  - selected custom `Other note` text also prints under item lines
  - spicy note aliases are symbol-only: `☆`, `☆☆`, `♥`, `♥♥`
  - if Side Dish (`S`) groups exist, they print after a full-width separator line
  - side dish labels are printed as plain names (no `S-` prefix)
  - takeaway items also print in a same-ticket boxed bag section below main lines:
    - grouped takeaway -> one bag per group id (ascending)
    - ungrouped takeaway -> one `DEFAULT` bag at the end
    - each bag has header ear `ᙏ`; grouped bags include one compact group-number line below
- If print fails after save, DB records remain (status becomes `PRINT_FAILED`)
