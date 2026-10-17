# Watch-cleanup reference

## Terminology
- **Fully watched** = Plex `viewCount >= 1` (completed playback).
- **Partially watched** = Plex has `viewOffset` set but no `viewCount` (started, unfinished).

## Plex queries (no token required)
| Goal | Endpoint |
|---|---|
| List libraries | `GET /library/sections` |
| Top-level movie items + view state | `GET /library/sections/1/all` |
| ALL items incl. episodes + view state | `GET /library/all?type=4&includeGuids=1` |

Episode fields of interest: `viewCount`, `viewOffset`, `grandparentTitle` (show),
`parentIndex` (season), `index` (episode), `ratingKey`, `title`.

## Deletion calls (worked in practice)
**Movies (Radarr):**
```bash
curl -X DELETE "$RADARR/api/v3/movie/{id}" -H "X-Api-Key: $KEY" \
     -H "Content-Type: application/json" \
     -d '{"addImportListExclusion":false}'
```

**Episode files (Sonarr):**
```bash
curl -X DELETE "$SONARR/api/v3/episodefile/{fileId}" -H "X-Api-Key: $KEY"
```
> Prefer this over the `/api/v3/command` `DeleteEpisodeFiles` POST, which can 500
> ("Sequence contains no matching element") on some builds.

**Un-monitor an episode (prevent re-grab):**
```bash
# GET the episode, set "monitored":false, PUT it back (returns 202 async)
curl -X PUT "$SONARR/api/v3/episode/{episodeId}" -H "X-Api-Key: $KEY" -H "Content-Type: application/json" -d @episode.json
```

## Matching gotchas
- Plex show title may differ slightly from Sonarr's (e.g. Plex "The Office" vs Sonarr
  "The Office (MX) La Oficina") — fall back to a stripped title match.
- Only delete episodes where Sonarr has a **file** (`episodeFileId` present). If unmonitored
  and re-downloaded, Plex still marks it watched (Tracks by episode), so it gets cleaned next pass.

## Post-delete
- Plex shows stale entries until its next library scan picks up the removed files.
- Confirm remaining watched episodes aren't still `monitored` (else they re-download).