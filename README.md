# SteamSearch

SteamSearch is a CS2 skin price query and opportunity scanning tool.

Current phase: lightweight browser preview with SQLite search and SteamDT live price support.

## Run

```bash
python3.12 -m app.main
```

Then open:

```text
http://127.0.0.1:8765
```

The first run creates local runtime folders and initializes `data/steamsearch.db`.

To run only bootstrap checks without starting the web server:

```bash
python3.12 -m app.main check
```

## Browser Preview

Configure SteamDT before starting if you want live data:

```bash
cp config/config.example.toml config/config.local.toml
# edit config/config.local.toml and set steamdt.api_key
```

Or use an environment variable:

```bash
export STEAMDT_API_KEY="your-api-key"
```

```bash
python3.12 -m app.ui.web_server
```

This is equivalent to:

```bash
python3.12 -m app.main web
```

The preview uses the real SQLite search path. If no SteamDT base data exists yet, it seeds local demo items for viewing.
Click "同步 SteamDT 基础库" in the browser to import real SteamDT base items into SQLite.

## Verify

```bash
python3.12 -m unittest
```
