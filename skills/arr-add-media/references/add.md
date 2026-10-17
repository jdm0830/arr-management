# Adding media — exact API shapes

## Lookup
- Sonarr: `GET {sonarr}/api/v3/series/lookup?term=<title or 'tvdb:ID'>`  → array of TMDB/TVDb hits
- Radarr: `GET {radarr}/api/v3/movie/lookup?term=<title>`  → array of TMDb hits

Prefers an exact-title match; fall back to the first hit with a sane year; confirm if ambiguous.

## Add (worked in practice)

### Sonarr — `POST {sonarr}/api/v3/series` (returns 201 + resource)
```json
{
  "tvdbId": 401879,
  "title": "The Last Days of Ptolemy Grey",
  "titleSlug": "the-last-days-of-ptolemy-grey",
  "qualityProfileId": 1,
  "rootFolderPath": "/data/shows1",
  "monitor": "all",
  "images": [],
  "seasons": [],
  "seriesType": "standard",
  "addOptions": { "searchForMissingEpisodes": true }
}
```

### Radarr — `POST {radarr}/api/v3/movie`
```json
{
  "tmdbId": 12345,
  "title": "Some Movie",
  "qualityProfileId": 1,
  "rootFolderPath": "/data/movies1",
  "monitor": "movieOnly",
  "images": [],
  "addOptions": { "searchForMovie": true }
}
```
Header: `X-Api-Key: <key>`, `Content-Type: application/json`.

## Current config
- Sonarr root `/data/shows1`, profile id 1 ("Any")
- Radarr root `/data/movies1`, profile id 1 ("Any")