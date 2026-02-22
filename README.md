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

## Controls

- `R` / `G` (normal mode): enter Ramyun or Gimbap search mode
- `T` (normal mode): add `Tteokbokki` directly to registered orders
- Type letters/numbers (active mode): build search query
- `Backspace` (active mode): delete one query character
- `Tab` / `↑` / `↓` (active mode): cycle search results
- `Enter` (active mode): register highlighted result into the left order panel
- `Ctrl+C`: exit active mode back to normal mode (no-op in normal mode)
- `Ctrl+Q`: quit app
