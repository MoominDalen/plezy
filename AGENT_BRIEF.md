# StockWatch — Agent Briefing (copy into a new Cloud Agent)

Use this document as the **full prompt** for a new Cursor Cloud Agent. Grant that agent access to the **private** repo:

**https://github.com/MoominDalen/StockWatch**

---

## Your mission

You are completing **StockWatch**: a macOS-native app that monitors **John Lewis** Pokemon TCG stock (URLs with `pokemon-tcg` in the slug) and **Pokemon Center UK** (`https://www.pokemoncenter.com/en-gb`) queue status, with optional Telegram alerts.

The codebase is largely implemented but may not be fully pushed to GitHub, and the **all-in-one DMG has not been successfully built/released yet**. Your job:

1. **Push** the full codebase to `MoominDalen/StockWatch` on `main`.
2. **Trigger** the GitHub Actions workflow **Build macOS DMG** (and/or tag `v1.0.0` for **Release DMG**).
3. **Fix any CI failures** until a `.dmg` artifact uploads successfully.
4. Optionally **remove** leftover StockWatch code from `MoominDalen/plezy` if a `stockwatch` branch still exists there.
5. Report the **download link** for the DMG (Actions artifact or Release).

Do **not** estimate timelines in days/weeks. Do execute: push, run workflows, read logs, patch, retry.

---

## Required GitHub permissions

The agent must have a token / GitHub App installation that can:

| Permission | Why |
|------------|-----|
| **Read/write** to `MoominDalen/StockWatch` | Push code, open PRs |
| **Actions: read + write** | Run workflows, download artifacts |
| **Contents: read + write** | Commits, releases |
| **Workflows: write** | `workflow_dispatch`, fix workflow files |

If push returns `Repository not found` or `403`, the integration is scoped only to `plezy` — **reconnect the agent with StockWatch selected** or use a PAT with `repo` scope on the user account.

---

## Product requirements (source of truth)

### John Lewis

- Poll stock every **2 seconds** by default (`POLL_INTERVAL_SECONDS`).
- Use John Lewis stock API: `POST https://www.johnlewis.com/fashion-ui/api/stock/v2` with JSON `{"skus":["..."]}` and headers `Origin`, `Referer`, `Content-Type: application/json`.
- **Fallback**: parse product HTML for `skuId`, `og:image`, Add to basket / availability.
- **Discovery**: scan search/category pages for product URLs where the path contains **`pokemon-tcg`** (slug), e.g. `/pokemon-tcg-.../p123456789`.
- **Alerts**: notify on transition **out of stock → in stock** (not on first run if already in stock).

### Pokemon Center UK

- Monitor `https://www.pokemoncenter.com/en-gb` (and optionally category pages).
- Detect queue via markers: `queue-it.net`, `Queue-it`, `_Incapsula_Resource`, waiting room copy, `"pos":` in responses.
- Telegram + UI alert when queue becomes active.

### macOS app (SwiftUI)

- **All-in-one**: app **auto-starts** bundled backend on launch (no Terminal for end users).
- UI: product **grid with images**, green/red borders, IN STOCK / OUT badges.
- Sidebar: backend status, **Scan John Lewis (pokemon-tcg)**, Pokemon Center UK panel, filters, Settings.
- CRUD: add/edit/delete product URLs in UI.
- Live updates via **WebSocket** `ws://127.0.0.1:8765/ws`.

### Telegram (optional)

- `python main.py` — BotFather token, `/start`, `/add <url>`, `/status`, `/list`.

### DMG deliverable

- Single **StockWatch.dmg**: drag app to Applications; backend embedded under `StockWatch.app/Contents/Resources/backend/`.
- Data dir: `~/Library/Application Support/StockWatch/data/`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  StockWatch.app (SwiftUI, macOS 13+)                     │
│  - BackendProcess.swift → launches bundled backend       │
│  - REST + WebSocket → 127.0.0.1:8765                     │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  stockwatch-backend (PyInstaller onedir)                 │
│  backend_entry.py → uvicorn api.server:app               │
│  jl_client.py, pc_client.py, discovery/, service.py      │
│  SQLite: Application Support/StockWatch/data/           │
└─────────────────────────────────────────────────────────┘
```

---

## Repository layout

```
StockWatch/
├── api/server.py              # FastAPI + WebSocket
├── backend_entry.py           # PyInstaller entrypoint
├── packaging/
│   ├── stockwatch-backend.spec
│   └── requirements-build.txt
├── discovery/johnlewis_scanner.py   # pokemon-tcg URL discovery
├── jl_client.py               # John Lewis stock API + HTML fallback
├── pc_client.py               # Pokemon Center UK queue detection
├── service.py                 # Monitor loop
├── database.py                # SQLite products + settings
├── scripts/
│   ├── build-dmg.sh           # macOS: PyInstaller + xcodebuild + hdiutil
│   └── create-github-repo.sh
├── macos/StockWatch/          # Xcode project (SwiftUI)
│   └── StockWatch/
│       ├── StockWatchApp.swift
│       ├── BackendProcess.swift
│       ├── AppState.swift, APIClient.swift, Models.swift
│       └── Views/ (RootView, ProductCardView, AddProductSheet, SettingsView)
├── .github/workflows/
│   ├── build-macos-dmg.yml    # workflow_dispatch + push → artifact
│   └── release-dmg.yml          # tags v* → GitHub Release + DMG
├── main.py, telegram_app.py   # Optional Telegram bot
├── requirements.txt
├── run_api.sh                 # Dev: API only
└── tests/
```

---

## Build DMG (local or CI)

### On GitHub Actions (preferred)

```bash
# After push to main:
gh workflow run build-macos-dmg.yml -R MoominDalen/StockWatch
# Or:
git tag v1.0.0 && git push origin v1.0.0   # triggers release-dmg.yml
```

Runner: **macos-14**. Artifact name: **StockWatch-macos-dmg**.

### On a Mac

```bash
chmod +x scripts/build-dmg.sh
./scripts/build-dmg.sh
# Output: build/dist/StockWatch-<version>.dmg
```

Steps inside script:

1. `pyinstaller packaging/stockwatch-backend.spec` → `build/pyinstaller/dist/stockwatch-backend/`
2. `xcodebuild -project macos/StockWatch/StockWatch.xcodeproj -scheme StockWatch -configuration Release`
3. Copy backend folder → `StockWatch.app/Contents/Resources/backend/`
4. `hdiutil create` → DMG with Applications symlink

---

## Common CI failures & fixes

| Failure | Fix |
|---------|-----|
| Workflow not found | Workflow file must exist on **default branch** (`main`). |
| PyInstaller missing modules | Add to `hiddenimports` in `packaging/stockwatch-backend.spec` (uvicorn, fastapi, starlette, httpx, etc.). |
| `xcodebuild` scheme not found | Open `project.pbxproj`; ensure `BackendProcess.swift` is in Compile Sources. |
| Codesign errors | Script sets `CODE_SIGNING_ALLOWED=NO` for CI; adjust for distribution if needed. |
| Backend not executable | `chmod +x` on `stockwatch-backend` after copy into `.app`. |
| John Lewis 403 in CI | Expected on cloud IPs; DMG still builds; runtime needs UK/home IP. |
| `SPECPATH` / paths in spec | `ROOT = Path(SPECPATH).parent` (parent of `packaging/` = repo root). |

---

## API reference (localhost:8765)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `{"status":"ok"}` |
| GET | `/products` | List watches |
| POST | `/products` | Add product |
| PUT | `/products/{id}` | Update |
| DELETE | `/products/{id}` | Delete |
| POST | `/scan/johnlewis` | Discover pokemon-tcg URLs |
| GET | `/pokemoncenter` | Queue status |
| POST | `/pokemoncenter/check` | Force check |
| WS | `/ws` | Live events: `product_updated`, `pokemoncenter_updated`, `scan_complete` |

---

## Git workflow for this agent

```bash
git clone https://github.com/MoominDalen/StockWatch.git
cd StockWatch
# If repo is empty, copy from plezy/stockwatch branch or local snapshot:
#   git fetch https://github.com/MoominDalen/plezy.git stockwatch:import
#   git merge import --allow-unrelated-histories
# Or restore from agent workspace if provided.

git add -A && git commit -m "..." && git push origin main
gh workflow run build-macos-dmg.yml -R MoominDalen/StockWatch
gh run watch -R MoominDalen/StockWatch
```

**Branch naming** (if agent creates branches): `cursor/<descriptive-name>-ebec`

---

## Success criteria

- [ ] `main` on `MoominDalen/StockWatch` contains full project (40+ files, macOS + Python + workflows).
- [ ] GitHub Actions **Build macOS DMG** completes green.
- [ ] Downloadable `.dmg` in Actions artifact or Release `v1.0.0`.
- [ ] README explains: install DMG → launch app → Scan → no Terminal.
- [ ] Unit tests pass: `PYTHONPATH=. python -m unittest discover -s tests`

---

## Future update ideas (after DMG ships)

1. **Menu bar app** — background monitoring without dock icon.
2. **macOS notifications** — `UNUserNotificationCenter` on restock (in addition to Telegram).
3. **Notarization & signing** — Apple Developer ID for Gatekeeper-friendly DMG.
4. **Auto-update** — Sparkle framework checking GitHub Releases.
5. **Pokemon Center browser helper** — optional Safari/Chrome extension for queue position (`pos` in Incapsula responses).
6. **Price history charts** — store price snapshots in SQLite.
7. **Multi-retailer** — Smyths, Argos, Very (same monitor pattern).
8. **iCloud sync** — watchlists across Macs.
9. **Configurable alert rules** — “any stock” vs “quantity ≥ N”.
10. **Sitemap crawler** — deeper John Lewis discovery beyond search pages.

---

## Plezy cleanup (optional)

StockWatch was removed from `MoominDalen/plezy` on branch `cursor/johnlewis-pokemon-stock-checker-ebec` (PR #2). A mirror branch `stockwatch` may still exist on plezy — delete that branch after StockWatch is canonical.

---

## One-shot agent prompt (paste below this line)

```
You are working on the private repo https://github.com/MoominDalen/StockWatch

Build and ship StockWatch: a macOS SwiftUI app with an embedded Python backend that:
- Monitors John Lewis Pokemon TCG products (pokemon-tcg slugs), polls every 2s, restock alerts
- Monitors Pokemon Center UK (en-gb) for queue/Queue-it activity
- Provides a native UI with product images, scan button, add/edit products, WebSocket live updates
- Ships as a single DMG (PyInstaller backend inside StockWatch.app, auto-started on launch)

Read AGENT_BRIEF.md in the repo (or this message) for architecture and file layout.

Tasks:
1. Ensure all code is on main and pushed.
2. Run/fix GitHub Actions "Build macOS DMG" until green; publish v1.0.0 release with DMG if needed.
3. Fix PyInstaller hiddenimports, Xcode project, workflow on default branch as needed.
4. Confirm tests pass.
5. Give the user the DMG download URL and brief install steps.

You have permission to create commits, push, run workflows, and create releases on MoominDalen/StockWatch.
Do not rebuild inside plezy unless StockWatch push fails—in that case fix permissions first.

When done, suggest 3-5 prioritized product improvements from the brief's "Future update ideas" section.
```

---

*Generated for handoff from Plezy cloud agent — May 2026*
