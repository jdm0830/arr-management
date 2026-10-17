# arr-stack

Shared configuration + HTTP helpers for an *arr media stack (Sonarr, Radarr, Plex, Prowlarr).

This is the **foundation layer** for home-media automation skills. It doesn't run anything on its
own — it knows *where your services live and how to authenticate*, so the other skills don't each
reinvent that.

## What it does

- **Holds your endpoints + API keys** (config file or environment — never in chat).
- **Provides HTTP helpers** so any skill can call Sonarr/Radarr/Plex consistently.
- **Health-checks the download pipeline** end-to-end.

Companion skills that build on this: `arr-add-media` (add TV/movies), `arr-watch-cleanup`
(delete watched media).

## Configuration

Nothing is hardcoded — you supply your own endpoints and keys.

**Resolution order (first hit per key wins):**
1. **Environment variables** (`SONARR_URL`, `SONARR_API_KEY`, …)
2. **Config file**: `$ARR_CONFIG`, else `<workspace>/.secrets/arr-keys.txt`,
   else `~/.config/arr-stack/arr-keys.txt`

**Config file format** (`KEY=VALUE`, `#` comments allowed):

```ini
# --- required ---
SONARR_URL=http://media-host:8989
SONARR_API_KEY=xxxxxxxxxxxxxxxx
RADARR_URL=http://media-host:7878
RADARR_API_KEY=xxxxxxxxxxxxxxxx
PLEX_URL=http://media-host:32400
PLEX_TOKEN=xxxxxxxxxxxx

# --- optional: Prowlarr ---
PROWLARR_URL=http://media-host:9696
PROWLARR_API_KEY=xxxxxxxxxxxx

# --- optional: download client (e.g. qBittorrent on a seedbox) ---
QBITTORRENT_URL=https://seed.example.com/qbittorrent
QBITTORRENT_HOST=seed.example.com
QBITTORRENT_USER=xxx
QBITTORRENT_PASS=xxx

# --- optional: Syncthing (remote/seed) ---
SYNCTHING_URL=https://seed.example.com/syncthing
SYNCTHING_USER=xxx
SYNCTHING_PASS=xxx
SYNCTHING_DEVICE_ID=XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX
SYNCTHING_LISTEN=tcp://seed.example.com:22000

# --- optional: Syncthing (media host) ---
MEDIA_SYNCTHING_URL=http://media-host:8384
MEDIA_SYNCTHING_APIKEY=xxxxxxxxxxxx
MEDIA_SYNCTHING_DEVICE_ID=XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX

# --- optional: media host SSH ---
MEDIA_HOST=media-host
MEDIA_SSH_USER=admin
MEDIA_SSH_PASS=xxx

# --- optional: path mapping + sync folder ---
SEED_PATH_HOST=seed.example.com
DOWNLOADS_FOLDER_ID=downloads
```

See `config.example` for a copy-paste template.

**Never commit your config.** Keep it in `.secrets/` (mode 600) or outside the repo entirely.

## Scripts

### `scripts/load.py`
Resolves config and prints it as JSON (or `--env` for `export VAR=val` lines).

```bash
python3 scripts/load.py                 # JSON
python3 scripts/load.py --env           # shell exports
python3 scripts/load.py --config PATH   # explicit config file
```

Fails loudly if `sonarr.url`, `radarr.url`, or `plex.url` aren't set.

### `scripts/health.py`
End-to-end pipeline check. Verifies, **without printing secrets**:
1. Sonarr/Radarr can reach their download client.
2. The download client answers its API.
3. Syncthing peers are paired and the configured folder is in sync.
4. Sonarr/Radarr have the expected remote path mapping.

```bash
python3 scripts/health.py     # exits non-zero on failure
```

Optional sections (qBittorrent, Syncthing, path mapping) are only checked when configured — a
minimal Sonarr+Radarr+Plex setup still works.

## Layout

```
SKILL.md                  # this file
config.example            # copy-paste config template
scripts/load.py           # config resolver + JSON/env output
scripts/health.py         # pipeline health check
references/stack.md       # topology notes: how seed -> media host sync works
```

## Notes

- **No credentials in this repo.** Ever.
- Keys go in the config file or environment; the helpers read them and never echo them.
- The `X-Api-Key` header is what Sonarr/Radarr accept — *not* the web-session cookie.

## Credits

Built by **jdm0830**.

## License

MIT — use it, fork it, improve it. A tip is appreciated but never expected.
