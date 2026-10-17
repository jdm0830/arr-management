---
name: arr-add-media
description: Add TV series (Sonarr) or movies (Radarr) to the home *arr stack. Use when the user asks to "add/show a new series/movie", "grab X", "set up a show", "monitor a season", etc. Looks up the title on the indexer, adds it with the right quality profile / root folder, and optionally starts an immediate search. Loads endpoints + keys from the arr-stack foundation. Companion to arr-watch-cleanup (deleting watched media).
---

# Arr Add Media

Add new **series** to Sonarr or **movies** to Radarr.

## Workflow
1. Load config with the arr-stack skill: `python3 {stack}/scripts/load.py`.
2. Look up the title:
   - Sonarr: `GET {sonarr}/api/v3/series/lookup?term={title}`
   - Radarr: `GET {radarr}/api/v3/movie/lookup?term={title}`
   Pick the intended hit (prefer exact title + sensible year). Confirm with the user if ambiguous.
3. Add it using the standard profile/root folder (see reference):
   - Sonarr: `POST {sonarr}/api/v3/series` with `tvdbId`, `title`, `qualityProfileId`, `rootFolderPath`, `monitor`, `addOptions.searchForMissingEpisodes`.
   - Radarr: `POST {radarr}/api/v3/movie` with `tmdbId`, `title`, `qualityProfileId`, `rootFolderPath`, `monitor`, `addOptions.searchForMovie`.
4. Report the new series/movie id + path, and whether the search was kicked off.

## Automation
- **`scripts/add_media.py add-series "<Title>"`** and **`add_media.py add-movie "<Title>"`**
  perform the lookup + add with sensible defaults, and print the result. Add `--search` to force a
  missing-content search (default on).

## Reference
Exact API call shapes and the current profile/root folder values: `references/add.md`.