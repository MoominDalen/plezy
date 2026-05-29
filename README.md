# StockWatch

macOS app to monitor **John Lewis** Pokemon TCG stock (`pokemon-tcg` URLs) and **Pokemon Center UK** queues — with optional Telegram alerts.

## Install (DMG — all-in-one)

1. Download the latest **`StockWatch-*.dmg`** from [GitHub Actions](../../actions) (workflow **Build macOS DMG**) or releases.
2. Open the DMG and drag **StockWatch** to **Applications**.
3. Launch **StockWatch** from Applications.

No Terminal, Python, or backend setup required — the app bundles and starts the API automatically.

Data is stored in `~/Library/Application Support/StockWatch/data/`.

## Features

- Product grid with **images** and in-stock indicators
- **Scan John Lewis** for URLs containing `pokemon-tcg` in the slug
- **Pokemon Center UK** queue status (`/en-gb`)
- Add / edit / delete watches in the UI
- Live updates via WebSocket
- Optional Telegram bot (`python main.py`)

## Build the DMG yourself (macOS)

```bash
git clone https://github.com/MoominDalen/StockWatch.git
cd StockWatch
chmod +x scripts/build-dmg.sh
./scripts/build-dmg.sh
open build/dist/
```

Requires Xcode 15+ and Python 3.10+.

## First-time repo setup (maintainers)

```bash
chmod +x scripts/create-github-repo.sh
./scripts/create-github-repo.sh
```

Or create a private repo named **StockWatch** on GitHub, then:

```bash
git remote add origin git@github.com:MoominDalen/StockWatch.git
git push -u origin main
```

## Development (backend only)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run_api.sh
open macos/StockWatch/StockWatch.xcodeproj
```

## License

Personal use; respect retailer terms of service.
