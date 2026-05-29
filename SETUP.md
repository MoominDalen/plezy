# Repository migration from Plezy

This project was moved out of [plezy](https://github.com/MoominDalen/plezy) into its own repository.

## Create the private GitHub repo

**Option A — GitHub CLI (recommended)**

```bash
gh auth login
./scripts/create-github-repo.sh
```

**Option B — Manual**

1. Open https://github.com/new?name=StockWatch&private=true  
2. Do **not** add a README (this repo already has one).  
3. Run:

```bash
git remote add origin git@github.com:MoominDalen/StockWatch.git
git branch -M main
git push -u origin main
```

## Build the DMG on GitHub

After pushing:

1. Go to **Actions** → **Build macOS DMG** → **Run workflow**.  
2. When finished, download the **StockWatch-macos-dmg** artifact.  
3. That file is your installable all-in-one app.

Or push a tag: `git tag v1.0.0 && git push origin v1.0.0`
