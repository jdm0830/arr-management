# arr-stack — topology notes

How a typical *arr download pipeline fits together: a remote **seed host** downloads, **Syncthing**
syncs the files down to the **media host**, and Sonarr/Radarr pick them up via a **remote path
mapping**.

```
┌─────────────┐   torrents    ┌──────────────┐   Syncthing   ┌──────────────┐
│  Indexer    │ ────────────► │  Seed host   │ ────────────► │  Media host  │
│ (Prowlarr)  │               │ (qBittorrent)│   (downloads) │ (Sonarr/     │
└─────────────┘               └──────────────┘               │  Radarr/Plex)│
                                                             └──────────────┘
```

## The pieces

| Component | Typical port | Notes |
|---|---|---|
| Sonarr (TV) | 8989 | API base `/api/v3`, auth via `X-Api-Key` |
| Radarr (movies) | 7878 | API base `/api/v3`, auth via `X-Api-Key` |
| Plex | 32400 | Library endpoints often work without a token; **history endpoints need one** |
| Prowlarr (indexers) | 9696 | API base `/api/v1` |
| Homarr / dashboard | varies | web login only |
| Download client (qBittorrent etc.) | varies | often on a **remote seed host** |
| Syncthing | 8384 (web UI) | syncs completed downloads → media host |

All endpoints are **yours to configure** — see `../config.example` and `../SKILL.md`. Nothing in
this repo hardcodes a host.

## How the pipeline works

1. **Indexer** (Prowlarr) feeds Sonarr/Radarr.
2. Sonarr/Radarr hand releases to the **download client**.
3. If the download client is on a **remote seed host**, completed files sit in a path that means
   nothing to the media host.
4. **Syncthing** mirrors that remote folder down to the media host (commonly one-way:
   seed → media, `receiveonly` on the local side so local content is never pushed back up).
5. Sonarr/Radarr need a **remote path mapping**: "when the download client says the file is at
   *remote path X*, it's actually at *local path Y* on my disk."
6. Sonarr/Radarr import the file into the library; Plex picks it up.

## The two things that break most often

**1. Remote path mapping drift.** If the seed path or local mount changes (new seed host, new
drive, renamed folder), Sonarr/Radarr can't find completed downloads. Symptom: "No files found
eligible for import." Fix: correct the mapping in Sonarr/Radarr settings, and update
`SEED_PATH_HOST` in your config.

**2. Syncthing desync.** If the seed peer disconnects or the folder is out of sync, imports stall.
Symptom: downloads complete remotely but never appear locally. Fix: check
`/rest/db/status?folder=<id>` for `needFiles > 0`, and `/rest/system/connections` for the peer's
`connected` flag. `scripts/health.py` checks both.

## API auth notes

- Sonarr/Radarr accept the **`X-Api-Key` header** (or `?apikey=` query param).
- They do **not** accept the web-session cookie — a browser login is not enough for API calls.
- A web UI login exists for each service but is separate from API auth.

## Syncthing API notes

- The web UI sets a **CSRF cookie**; API calls need `X-CSRF-Token-<instance>` plus the API key.
- Folder id must match on both sides (commonly `downloads`; configurable as
  `DOWNLOADS_FOLDER_ID`).
- Device IDs are per-installation and should stay in your private config, not in a repo.

## Design note

Keep the topology in your head, and the **values** in your config. That's why this skill ships a
`config.example` with placeholders and reads everything at runtime — so a stack stays private while
the *pattern* stays shareable.
