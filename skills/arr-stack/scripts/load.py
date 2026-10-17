#!/usr/bin/env python3
"""Load Sonarr/Radarr/Plex endpoints + API keys for an *arr media stack.

Prints a JSON object to stdout:
{
  "sonarr": {"url": ..., "apiKey": ***},
  "radarr": {"url": ..., "apiKey": ***},
  "plex":   {"url": ...}
}

CONFIG RESOLUTION ORDER (first hit wins, per key):
  1. Environment variables (e.g. SONARR_URL, SONARR_API_KEY)
  2. A config file:  $ARR_CONFIG  or  <workspace>/.secrets/arr-keys.txt
                    or  ~/.config/arr-stack/arr-keys.txt
  Config file format: KEY=VALUE lines, # comments allowed.

No values are ever printed unless explicitly requested. Fails loudly if
required keys (sonarr/radarr/plex url) are missing.

Usage:
    python3 load.py                # print JSON
    python3 load.py --env          # print as `export VAR=val` lines
    python3 load.py --config PATH  # use a specific config file
"""
import json
import os
import sys

# KEY -> (section, destkey)
MAPPING = {
    # Sonarr / Radarr / Plex (required)
    "SONARR_URL":     ("sonarr", "url"),
    "SONARR_API_KEY": ("sonarr", "apiKey"),
    "RADARR_URL":     ("radarr", "url"),
    "RADARR_API_KEY": ("radarr", "apiKey"),
    "PLEX_URL":       ("plex", "url"),
    "PLEX_TOKEN":     ("plex", "token"),
    "PROWLARR_URL":   ("prowlarr", "url"),
    "PROWLARR_API_KEY": ("prowlarr", "apiKey"),
    # Download client (e.g. qBittorrent on a seedbox)
    "QBITTORRENT_URL":  ("qbittorrent", "url"),
    "QBITTORRENT_HOST": ("qbittorrent", "host"),
    "QBITTORRENT_USER": ("qbittorrent", "user"),
    "QBITTORRENT_PASS": ("qbittorrent", "pass"),
    # Syncthing on the remote/seed host
    "SYNCTHING_URL":       ("syncthing_seed", "url"),
    "SYNCTHING_USER":      ("syncthing_seed", "user"),
    "SYNCTHING_PASS":      ("syncthing_seed", "pass"),
    "SYNCTHING_DEVICE_ID": ("syncthing_seed", "deviceId"),
    "SYNCTHING_LISTEN":    ("syncthing_seed", "listen"),
    # Syncthing on the media host
    "MEDIA_SYNCTHING_URL":       ("syncthing_local", "url"),
    "MEDIA_SYNCTHING_APIKEY":    ("syncthing_local", "apiKey"),
    "MEDIA_SYNCTHING_INSTANCE":  ("syncthing_local", "instance"),
    "MEDIA_SYNCTHING_DEVICE_ID": ("syncthing_local", "deviceId"),
    # Media host SSH
    "MEDIA_HOST":     ("media_host", "host"),
    "MEDIA_SSH_USER": ("media_host", "sshUser"),
    "MEDIA_SSH_PASS": ("media_host", "sshPass"),
    # Remote path mapping host (the seed hostname as Sonarr/Radarr know it)
    "SEED_PATH_HOST": ("pathmap", "host"),
    "DOWNLOADS_FOLDER_ID": ("syncthing_local", "folderId"),
}

SECTIONS = ("sonarr", "radarr", "plex", "prowlarr", "qbittorrent",
            "syncthing_seed", "syncthing_local", "media_host", "pathmap")


def _candidate_config_paths(explicit=None):
    if explicit:
        return [explicit]
    out = []
    if os.environ.get("ARR_CONFIG"):
        out.append(os.environ["ARR_CONFIG"])
    # workspace root (skills/<name>/scripts -> up 3), if it exists
    here = os.path.dirname(os.path.abspath(__file__))
    ws = os.path.abspath(os.path.join(here, "..", "..", ".."))
    out.append(os.path.join(ws, ".secrets", "arr-keys.txt"))
    # user-level fallback
    out.append(os.path.expanduser("~/.config/arr-stack/arr-keys.txt"))
    return out


def _read_config_file(path):
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if k in MAPPING:
                data[k] = v.strip()
    return data


def load_dict(config_path=None):
    data = {s: {} for s in SECTIONS}

    # 2) file layer
    file_vals = {}
    for p in _candidate_config_paths(config_path):
        file_vals = _read_config_file(p)
        if file_vals:
            break

    # 1) env layer overrides file layer
    for key, (section, dest) in MAPPING.items():
        val = os.environ.get(key)
        if val is None:
            val = file_vals.get(key)
        if val:
            data[section][dest] = val

    # required checks
    for name in ("sonarr", "radarr", "plex"):
        if not data[name].get("url"):
            sys.stderr.write(
                f"error: {name}.url not configured. Set {name.upper()}_URL "
                f"or add it to a config file (see --help / ARR_CONFIG).\n"
            )
            sys.exit(1)
    return data


if __name__ == "__main__":
    explicit = None
    if "--config" in sys.argv:
        i = sys.argv.index("--config")
        explicit = sys.argv[i + 1] if i + 1 < len(sys.argv) else None

    d = load_dict(explicit)
    if "--env" in sys.argv:
        for key in ("SONARR_URL", "SONARR_API_KEY", "RADARR_URL", "RADARR_API_KEY", "PLEX_URL"):
            if d.get(key.split("_")[0].lower(), {}).get("url") or d.get("sonarr", {}).get("apiKey"):
                pass
        print(f"export SONARR_URL={d['sonarr'].get('url','')}")
        print(f"export SONARR_API_KEY={d['sonarr'].get('apiKey','')}")
        print(f"export RADARR_URL={d['radarr'].get('url','')}")
        print(f"export RADARR_API_KEY={d['radarr'].get('apiKey','')}")
        print(f"export PLEX_URL={d['plex'].get('url','')}")
    else:
        print(json.dumps(d))
