# John Lewis Pokemon Card Stock Checker (Telegram)

Monitors [John Lewis](https://www.johnlewis.com) product pages for Pokemon TCG stock and sends **instant Telegram alerts** when items come back in stock.

Default poll interval is **2 seconds** (configurable). Alerts fire on restocks (out of stock → in stock), not on every poll.

## What you need

- Python 3.10+
- A Telegram account
- A machine that can reach `johnlewis.com` (UK home broadband/VPS works best; some cloud IPs are blocked)

## Quick start

### 1. Create a Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts.
3. Copy the **bot token** (looks like `123456789:ABC...`).

### 2. Get your chat ID (optional but recommended)

Either:

- Message [@userinfobot](https://t.me/userinfobot) and copy your **Id**, or
- Start your new bot and send `/start` — the checker registers your chat automatically.

### 3. Install and configure

```bash
cd johnlewis-pokemon-stock-checker
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
cp config.yaml.example config.yaml
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_CHAT_ID=your_numeric_chat_id
POLL_INTERVAL_SECONDS=2
```

Edit `config.yaml` and add **product page URLs** from John Lewis (not search pages unless you enable search mode):

```yaml
products:
  - name: "Pokemon TCG Booster"
    url: "https://www.johnlewis.com/your-product-slug/p123456789"
    sku: ""
```

To find URLs: search [johnlewis.com](https://www.johnlewis.com/search?search-term=pokemon+cards), open a product, copy the address bar link.

### 4. Run

```bash
python main.py
```

In Telegram, open your bot and send **`/start`**.

Leave the process running (Raspberry Pi, home PC, or VPS). When stock appears, you get a message with the product link.

## Telegram commands

| Command | Description |
|--------|-------------|
| `/start` | Register for alerts and show help |
| `/status` | Check current stock now |
| `/add <url>` | Add a John Lewis product URL to the watchlist |
| `/list` | Show watched products |
| `/help` | Same as `/start` |

Example:

```
/add https://www.johnlewis.com/some-pokemon-product/p113617158
```

## Instant notifications

- **`POLL_INTERVAL_SECONDS=2`** — checks every 2 seconds (minimum 1).
- Uses John Lewis’s stock API when available, with a page-parse fallback.
- Notifies when status changes **out of stock → in stock** (avoids spam on startup if already in stock).

For the fastest alerts, run on a stable UK connection and avoid intervals below 1 second (unnecessary load).

## Optional: watch search results

In `config.yaml`:

```yaml
search:
  enabled: true
  url: "https://www.johnlewis.com/search?search-term=pokemon+cards"
  max_products: 20
```

This discovers product links from search/category pages. Prefer explicit product URLs for reliability.

## Run in the background (Linux)

```bash
# Example systemd user service — adjust paths
cat > ~/.config/systemd/user/jl-pokemon-stock.service << 'EOF'
[Unit]
Description=John Lewis Pokemon stock checker
After=network-online.target

[Service]
WorkingDirectory=/path/to/johnlewis-pokemon-stock-checker
EnvironmentFile=/path/to/johnlewis-pokemon-stock-checker/.env
ExecStart=/path/to/johnlewis-pokemon-stock-checker/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user enable --now jl-pokemon-stock.service
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No alerts | Send `/start` to the bot; set `TELEGRAM_CHAT_ID` in `.env` |
| `No SKU found` | Open the product page → View Source → search `skuId` → put value in `sku:` in config |
| Timeouts / errors | John Lewis may block datacenter IPs; run from home UK network |
| Already in stock on first run | Normal — you only get alerted on the next **restock** |

## Project layout

```
johnlewis-pokemon-stock-checker/
  main.py              # Entry point
  telegram_app.py      # Bot + notification delivery
  monitor.py           # Polling loop
  jl_client.py         # John Lewis stock API / page parsing
  config.yaml          # Your watchlist (create from example)
  data/                # State + registered chat IDs (auto-created)
```

## Legal / polite use

Use reasonable poll intervals. This tool is for personal restock alerts only; respect John Lewis terms of service.
