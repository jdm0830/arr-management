---
name: arr-watch-cleanup
description: Delete already-watched media from the home *arr stack. When the user asks to "delete watched/seen media", "clean up what we've already watched", "purge viewed movies/episodes", or similar, use this skill after loading the arr-stack foundation. Cross-references Plex watch history (viewCount) against Sonarr (TV episodes) and Radarr (movies), then deletes watched movie files/entries and watched episode files while un-monitoring those episodes. Always confirm a dry-run plan with the user before deleting anything. Companion to arr-add-media (adding shows/movies) and arr-stack (config/keys).
---

# Arr Watch Cleanup

Delete media that has already been watched, using Plex watched-state as the source of truth.

## Workflow
1. **Load endpoints/keys** from the arr-stack skill: `python3 {stack}/scripts/load.py`.
2. **Survey watched content from Plex** (no token needed for the `type=4` dump):
   - Movies: `GET {plex}/library/sections/1/all` → items with `viewCount`.
   - TV episodes: `GET {plex}/library/all?type=4&includeGuids=1` → episodes with `viewCount`,
     joined to show via `grandparentTitle`, season via `parentIndex`, episode via `index`.
   - Treat `viewCount >= 1` as **fully watched**, `viewOffset` without `viewCount` as **partially watched**.
3. **Cross-reference against the arr libraries** so we only delete things we actually hold:
   - Radarr movies: `GET {radarr}/api/v3/movie` → match by title.
   - Sonarr episodes: `GET {sonarr}/api/v3/episode?seriesId={id}` → match show+season+ep → the
     `episodeFileId` is what gets deleted.
4. **Present the deletion plan and get explicit confirmation** from the user (they may want
   "watched only" vs "watched + partial"). Default: delete fully-watched movies + fully-watched episodes.
5. Execute deletions (see reference for exact calls) and un-monitor watched episodes so they don't re-grab.
6. Report what was deleted + what was skipped.

## Automation
- **`scripts/cleanup_watched.py`** performs steps 1–6 with a `--apply` flag:
  - Default (`dry-run`): prints the full plan, deletes nothing.
  - `--apply`: executes the deletions after you've shown the plan and the user confirms.
  - `--partial`: also include partially-watched (viewOffset) items.
  - This guards against accidental permanent removal. Always run dry-run first, show the user, then `--apply`.

## Key gotchas
- If Plex still lists an episode/movie after deletion, it just hasn't re-scanned — it clears on the next library scan.
- Deleting an episode file while the episode is still **monitored** makes Sonarr re-grab it → always un-monitor (set `monitored=false`) the deleted (watched) episodes.
- If the Sonarr/Radarr API returns 401, load a fresh key (see arr-stack `references/stack.md`).

## Reference
Detailed endpoints and deletion calls: `references/cleanup.md`.