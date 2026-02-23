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

### Normal mode

- `R` / `G`: enter Ramyun or Gimbap search mode
- `T`: add `Tteokbokki` directly to registered orders
- `J` / `K`: move register selection next / previous (wraps)
- `N`: open notes modal for selected register item
- `Ctrl+C`: no-op
- `Ctrl+Q`: quit app

### Active mode

- Type letters/numbers: build search query
- `Backspace`: delete one query character
- `Tab` / `↑` / `↓`: cycle search results
- `Enter`: register highlighted result into the left order panel
- `Ctrl+C`: exit active mode back to normal mode
- `Ctrl+Q`: quit app

### Notes modal

- `J` / `K` / `↑` / `↓`: move note cursor
- `Enter`: toggle highlighted note on/off
- `Esc` / `q` / `Ctrl+C`: close modal
