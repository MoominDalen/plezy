# StockWatch — John Lewis & Pokemon Center UK

Monitor **John Lewis** Pokemon TCG products and **Pokemon Center UK** queues, with instant Telegram alerts and a **native macOS app**.

## Features

| Feature | Description |
|--------|-------------|
| John Lewis stock | Polls every 2s (configurable), restock alerts |
| `pokemon-tcg` discovery | Scans John Lewis for product URLs with `pokemon-tcg` in the slug |
| Product images | Cards show og:image / CDN thumbnails in the macOS UI |
| Pokemon Center UK | Monitors [pokemoncenter.com/en-gb](https://www.pokemoncenter.com/en-gb) for queue / Queue-it |
| macOS app | SwiftUI UI — add, edit, scan, live updates via WebSocket |
| Telegram bot | Optional CLI bot (`python main.py`) |

---

## macOS app (recommended)

See **[macos/README.md](macos/README.md)** for full steps.

1. Start backend: `./run_api.sh`
2. Open `macos/StockWatch/StockWatch.xcodeproj` in Xcode → Run
3. Click **Scan John Lewis (pokemon-tcg)** in the sidebar
4. Watch the product grid; green border = in stock

---

## Telegram-only mode

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # TELEGRAM_BOT_TOKEN, etc.
cp config.yaml.example config.yaml
python main.py
```

Send `/start` to your bot, `/add <johnlewis-url>`, `/status`.

---

## API (for the Mac app or automation)

With `./run_api.sh` running:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/products` | List watches |
| POST | `/products` | Add product |
| POST | `/scan/johnlewis` | Discover `pokemon-tcg` URLs |
| GET | `/pokemoncenter` | UK queue status |
| WS | `/ws` | Live updates |

---

## Project layout

```
johnlewis-pokemon-stock-checker/
  api/server.py          # FastAPI + WebSocket
  discovery/             # pokemon-tcg URL scanner
  pc_client.py           # Pokemon Center UK queue detection
  macos/StockWatch/      # SwiftUI macOS app
  run_api.sh             # Start backend
  main.py                # Telegram bot entry
```

---

## Troubleshooting

- **Backend offline in app** — Run `./run_api.sh` from this folder first.
- **403 / timeouts** — Run on a UK home connection; many cloud IPs are blocked.
- **No SKU** — Set `sku` manually from page source (`skuId`).

Use reasonable poll intervals and personal use only.
