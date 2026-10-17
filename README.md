# arr-management

Manage a home **\*arr media stack** — add TV series and movies, clean up what you've already
watched, and health-check the whole download pipeline.

One install, three focused skills. The plumbing (endpoints, keys, path mapping) is handled for you;
the value is in the features.

> ⚠️ **EXPERIMENTAL.** This is a bundle plugin, and OpenClaw's bundle/plugin surface is still
> experimental — it can change between host versions. Built and tested against one host. Pin your
> version and re-verify after upgrades. See [Reporting broken things](#reporting-broken-things).

## What's inside

| Skill | What it does |
|---|---|
| **`arr-stack`** | The config/plumbing layer. Knows where Sonarr, Radarr, and Plex live and how to authenticate. Shared by the other two. |
| **`arr-add-media`** | Add a TV series (Sonarr) or movie (Radarr) — looks up the title, picks the right quality profile + root folder, optionally starts an immediate search. |
| **`arr-watch-cleanup`** | Delete media you've already watched. Cross-references Plex watch history against Sonarr/Radarr, then deletes watched files/entries and un-monitors those episodes. Always dry-runs first. |

## Install

```bash
openclaw plugins install clawhub:arr-management
```

Then restart or start the Gateway. The three skills become available in the next session.

## Setup

All three skills share one config. Nothing is hardcoded — you supply your own endpoints and keys.

**Resolution order (first hit per key wins):**
1. **Environment variables** (`SONARR_URL`, `SONARR_API_KEY`, …)
2. **Config file**: `$ARR_CONFIG`, else `<workspace>/.secrets/arr-keys.txt`,
   else `~/.config/arr-stack/arr-keys.txt`

See `skills/arr-stack/config.example` for a ready-to-copy template, and
`skills/arr-stack/SKILL.md` for the full key list.

```bash
# quick start
mkdir -p ~/.config/arr-stack
cp skills/arr-stack/config.example ~/.config/arr-stack/arr-keys.txt
$EDITOR ~/.config/arr-stack/arr-keys.txt
chmod 600 ~/.config/arr-stack/arr-keys.txt
```

**Never commit your config.** Keep it out of the repo; mode 600.

## Verify

```bash
python3 skills/arr-stack/scripts/health.py
```

Checks that Sonarr/Radarr reach their download client, the client's API answers, Syncthing peers are
paired and in sync, and remote path mappings are present. Exits non-zero on failure.

## Common tasks

```
"Add Severance to Sonarr"
"Grab the new Dune movie"
"What have we watched that we can delete?"
"Set up show X and start searching for it"
```

## Notes

- **Read-only where it matters.** `arr-add-media` adds; `arr-watch-cleanup` dry-runs and asks before
  deleting. Neither touches files without a confirmed plan.
- **No credentials ship with this plugin.** Everything is read from your config at runtime.
- The bundled `arr-stack` skill also works standalone if you place the three skill folders under a
  shared `skills/` directory.

## Reporting broken things

This is experimental, so things *will* occasionally break. If they do, open an issue with:
**what you did, what you expected, what actually happened**, plus `openclaw --version` and how you
installed it.

Known-fragile spots to watch:

- **Bundle detection / skill loading** — if the three skills don't appear after install, the host's
  `skills/` mapping may have changed. Check `openclaw plugins inspect arr-management` shows
  `Format: bundle`.
- **Config resolution** — `arr-stack` walks env → config file → fallback. If endpoints stop
  resolving after an upgrade, that order (or `ARR_CONFIG`) may have shifted.
- **Script path-walk** — dependent scripts locate `arr-stack/scripts/load.py` via `$ARR_STACK_DIR`
  → bundle layout → legacy layout. If that breaks you'll see `arr-stack load.py not found`.

Don't silently upgrade-and-pray — bundles are the most version-sensitive thing here.

## Credits

Built by **jdm0830**.

## License

MIT — use it, fork it, improve it. Experimental software; see the warning at the top.
