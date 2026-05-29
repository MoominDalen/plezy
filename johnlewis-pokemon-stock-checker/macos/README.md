# StockWatch macOS app

Native SwiftUI app for managing John Lewis Pokemon TCG watches and Pokemon Center UK queue status.

## Requirements

- macOS 13+
- Xcode 15+
- Python 3.10+ (for the local backend)

## Run (two terminals)

### Terminal 1 — backend

```bash
cd johnlewis-pokemon-stock-checker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run_api.sh
```

API listens on `http://127.0.0.1:8765`.

### Terminal 2 — macOS app

```bash
open macos/StockWatch/StockWatch.xcodeproj
```

In Xcode, select the **StockWatch** scheme and press **Run** (⌘R).

## Using the app

1. Confirm the sidebar shows **Backend connected** (green dot).
2. Click **Scan John Lewis (pokemon-tcg)** to discover product URLs whose path contains `pokemon-tcg`.
3. Product cards show **images**, green/red borders, and stock badges.
4. **Pokemon Center UK** panel shows queue status for `https://www.pokemoncenter.com/en-gb`.
5. Use **Add product URL** or **Edit** on any card to manage watches.
6. **Settings** — API URL, poll interval, optional Telegram fields.

Changes save to `data/stockwatch.db` and update live over WebSocket.

## Notes

- John Lewis and Pokemon Center may block datacenter IPs; run the backend on your Mac.
- For Telegram alerts, keep using `python main.py` or wire tokens in Settings (stored in SQLite).
