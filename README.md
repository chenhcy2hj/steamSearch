# SteamSearch

SteamSearch is a CS2 skin price query and opportunity scanning tool.

Current phase: Step 1 project skeleton.

## Run

```bash
python3.12 -m app.main
```

The first run creates local runtime folders and initializes `data/steamsearch.db`.

## Browser Preview

```bash
python3.12 -m app.ui.web_server
```

Then open:

```text
http://127.0.0.1:8765
```

The preview uses the real SQLite search path. If no SteamDT base data exists yet, it seeds local demo items for viewing.

## Verify

```bash
python3.12 -m unittest
```
