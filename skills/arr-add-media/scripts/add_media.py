#!/usr/bin/env python3
"""Add a TV series (Sonarr) or movie (Radarr) to the *arr stack.

Usage:
  python3 add_media.py add-series "<title>"
  python3 add_media.py add-movie  "<title>"
  python3 add_media.py add-series "<title>" --no-search

Loads endpoints/keys from arr-stack load.py. Prints the added entry's id + path.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

def _find_stack_dir():
    """Locate the arr-stack config layer.

    Works both in a standalone skills/ layout (sibling skill) and inside the
    arr-management bundle (skills/arr-stack). Also honours $ARR_STACK_DIR.
    """
    env = os.environ.get("ARR_STACK_DIR")
    if env and os.path.isfile(os.path.join(env, "scripts", "load.py")):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    # skills/<this-skill>/scripts -> up 2 = skills/ ; then arr-stack
    skills_root = os.path.abspath(os.path.join(here, "..", ".."))
    for cand in (
        os.path.join(skills_root, "arr-stack"),                       # bundle layout
        os.path.join(skills_root, "..", "arr-stack"),                 # legacy layout
    ):
        if os.path.isfile(os.path.join(cand, "scripts", "load.py")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(skills_root, "arr-stack"))


STACK_DIR = _find_stack_dir()
sys.path.insert(0, os.path.join(STACK_DIR, "scripts"))
try:
    import load as arrload
except Exception:
    arrload = None

# Defaults (see arr-stack references/stack.md)
SONARR_QP = 1          # quality profile "Any"
SONARR_ROOT = "/data/shows1"
RADARR_QP = 1
RADARR_ROOT = "/data/movies1"


def http(url, method="GET", key=None, body=None, timeout=30):
    headers = {"X-Api-Key": key} if key else {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def add_series(cfg, title, search=True):
    su = cfg["sonarr"]["url"]; sk = cfg["sonarr"]["apiKey"]
    hits = http(f"{su}/api/v3/series/lookup?term={urllib.parse.quote(title)}", key=sk)
    if not hits:
        sys.exit(f"no results for '{title}'")
    hit = next((h for h in hits if h.get("title", "").lower().strip() == title.lower().strip()), hits[0])
    payload = {
        "tvdbId": hit["tvdbId"],
        "title": hit["title"],
        "titleSlug": hit.get("titleSlug"),
        "qualityProfileId": SONARR_QP,
        "rootFolderPath": SONARR_ROOT,
        "monitor": "all",
        "images": hit.get("images", []),
        "seasons": hit.get("seasons", []),
        "seriesType": hit.get("seriesType", "standard"),
        "addOptions": {"searchForMissingEpisodes": search},
    }
    res = http(f"{su}/api/v3/series", method="POST", key=sk, body=payload)
    print(f"Added series: {res.get('title')} (id={res.get('id')}) -> {res.get('path')}")
    if search:
        print("  searchForMissingEpisodes: ON")


def add_movie(cfg, title, search=True):
    ru = cfg["radarr"]["url"]; rk = cfg["radarr"]["apiKey"]
    hits = http(f"{ru}/api/v3/movie/lookup?term={urllib.parse.quote(title)}", key=rk)
    if not hits:
        sys.exit(f"no results for '{title}'")
    hit = next((h for h in hits if h.get("title", "").lower().strip() == title.lower().strip()), hits[0])
    payload = {
        "tmdbId": hit["tmdbId"],
        "title": hit["title"],
        "qualityProfileId": RADARR_QP,
        "rootFolderPath": RADARR_ROOT,
        "monitor": "movieOnly",
        "images": hit.get("images", []),
        "addOptions": {"searchForMovie": search},
    }
    res = http(f"{ru}/api/v3/movie", method="POST", key=rk, body=payload)
    print(f"Added movie: {res.get('title')} (id={res.get('id')}) -> {res.get('path')}")
    if search:
        print("  searchForMovie: ON")


def main():
    if arrload is None:
        sys.exit("arr-stack load.py not found (looked in %s)" % STACK_DIR)
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add-series"); s.add_argument("title"); s.add_argument("--no-search", action="store_true")
    m = sub.add_parser("add-movie"); m.add_argument("title"); m.add_argument("--no-search", action="store_true")
    args = ap.parse_args()
    cfg = arrload.load_dict()
    if args.cmd == "add-series":
        add_series(cfg, args.title, search=not args.no_search)
    else:
        add_movie(cfg, args.title, search=not args.no_search)


if __name__ == "__main__":
    main()