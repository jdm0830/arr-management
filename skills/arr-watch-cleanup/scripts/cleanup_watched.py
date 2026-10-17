#!/usr/bin/env python3
"""Delete already-watched media from Sonarr/Radarr based on Plex watch history.

Source of truth: Plex (viewCount = fully watched, viewOffset = partial).

Cross-references:
  - Movies  -> Radarr (by title)  -> DELETE /api/v3/movie/{id}
  - Episodes-> Sonarr (show/season/episode) -> DELETE /api/v3/episodefile/{id} + unmonitor

Usage:
  python3 cleanup_watched.py                # DRY RUN: print plan, change nothing
  python3 cleanup_watched.py --apply        # execute deletions (movies + watched episodes)
  python3 cleanup_watched.py --apply --partial   # also include partially-watched items

Requires the arr-stack skill's load.py (reads .secrets/arr-keys.txt). Never prints API keys.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# --- locate arr-stack load.py (standalone skills/ layout or bundle layout) ---
def _find_stack_dir():
    env = os.environ.get("ARR_STACK_DIR")
    if env and os.path.isfile(os.path.join(env, "scripts", "load.py")):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    skills_root = os.path.abspath(os.path.join(here, "..", ".."))
    for cand in (
        os.path.join(skills_root, "arr-stack"),        # bundle layout
        os.path.join(skills_root, "..", "arr-stack"),  # legacy layout
    ):
        if os.path.isfile(os.path.join(cand, "scripts", "load.py")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(skills_root, "arr-stack"))


STACK_DIR = _find_stack_dir()
sys.path.insert(0, os.path.join(STACK_DIR, "scripts"))
try:
    import load as arrload
except Exception:  # fallback: import by path
    arrload = None


def http(url, method="GET", key=None, body=None, timeout=20):
    headers = {}
    if key:
        headers["X-Api-Key"] = key
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def plex_get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually delete (default dry-run)")
    ap.add_argument("--partial", action="store_true", help="also delete partially-watched items")
    args = ap.parse_args()

    if arrload is None:
        sys.exit("arr-stack load.py not found (looked in %s)" % STACK_DIR)
    cfg = arrload.load_dict()
    son = cfg["sonarr"]; rad = cfg["radarr"]
    SU = son["url"]; SK = son["apiKey"]
    RU = rad["url"]; RK = rad["apiKey"]
    PU = cfg["plex"]["url"]

    plan = {"movies": [], "episodes": []}  # each: {desc, delete} 

    # ---------- MOVIES ----------
    plex_m = plex_get(f"{PU}/library/sections/1/all")
    plex_m = plex_m["MediaContainer"].get("Metadata", [])
    st, rad_m = http(f"{RU}/api/v3/movie", key=RK)
    rad_titles = {m["title"]: m for m in rad_m if m.get("hasFile")}

    for it in plex_m:
        t = it.get("title")
        if not t or t not in rad_titles:
            continue
        if it.get("viewCount") or (args.partial and it.get("viewOffset")):
            rid = rad_titles[t]["id"]
            plan["movies"].append({"title": t, "id": rid, "watched": bool(it.get("viewCount"))})

    # ---------- TV EPISODES ----------
    all_items = plex_get(f"{PU}/library/all?type=4&includeGuids=1")
    watched_eps = [e for e in all_items["MediaContainer"].get("Metadata", [])
                   if e.get("viewCount") or (args.partial and e.get("viewOffset"))]

    st, son_series = http(f"{SU}/api/v3/series", key=SK)
    # map show title -> sonarr series
    series_by_title = {s["title"].lower(): s for s in son_series}

    # cache episode lists per seriesId
    ep_cache = {}

    for e in watched_eps:
        show = e.get("grandparentTitle")
        if not show:
            continue
        sd = series_by_title.get(show.lower())
        if not sd:
            # try to match by comparing stripped title (e.g. Plex "South Park" == Sonarr "South Park")
            cand = [s for s in son_series if s["title"].lower().replace(" (mx)", "").strip() == show.lower().strip()]
            sd = cand[0] if cand else None
        if not sd:
            continue
        sid = sd["id"]
        if sid not in ep_cache:
            st, eps = http(f"{SU}/api/v3/episode?seriesId={sid}", key=SK)
            ep_cache[sid] = eps or []
        season, epnum = e.get("parentIndex"), e.get("index")
        match = next((x for x in ep_cache[sid]
                      if x.get("seasonNumber") == season and x.get("episodeNumber") == epnum
                      and x.get("episodeFileId")), None)
        if match:
            plan["episodes"].append({
                "show": sd["title"], "season": season, "ep": epnum,
                "title": e.get("title"), "episodeId": match["id"],
                "fileId": match["episodeFileId"], "watched": bool(e.get("viewCount")),
            })

    # ---------- REPORT ----------
    print("=" * 60)
    print(f"PLAN ({'DRY RUN - nothing deleted' if not args.apply else 'APPLY'})")
    print(f"  movies:   {len(plan['movies'])}")
    print(f"  episodes: {len(plan['episodes'])}")
    for m in plan["movies"]:
        print(f"   [movie] {m['title']}  (id={m['id']}, watched={m['watched']})")
    for e in plan["episodes"]:
        print(f"   [ep] {e['show']} S{e['season']}E{e['ep']}  (epId={e['episodeId']} file={e['fileId']} watched={e['watched']})")

    if not args.apply:
        print("\nRe-run with --apply to execute (after user confirms).")
        return

    if not (plan["movies"] or plan["episodes"]):
        print("Nothing to delete.")
        return

    # ---------- EXECUTE ----------
    dels = 0
    for m in plan["movies"]:
        st, _ = http(f"{RU}/api/v3/movie/{m['id']}", method="DELETE", key=RK,
                     body={"addImportListExclusion": False})
        print(f"   delete movie {m['title']} -> HTTP {st}")
        dels += 1 if st == 200 else 0
    for e in plan["episodes"]:
        st, _ = http(f"{SU}/api/v3/episodefile/{e['fileId']}", method="DELETE", key=SK)
        print(f"   delete file {e['show']} S{e['season']}E{e['ep']} -> HTTP {st}")
        if st == 200:
            dels += 1
            # unmonitor so it doesn't re-download
            st3, epobj = http(f"{SU}/api/v3/episode/{e['episodeId']}", key=SK)
            if epobj:
                epobj["monitored"] = False
                st4, _ = http(f"{SU}/api/v3/episode/{e['episodeId']}", method="PUT", key=SK, body=epobj)
                print(f"      unmonitor S{e['season']}E{e['ep']} -> HTTP {st4}")
    print(f"DONE. {dels} items deleted.")


if __name__ == "__main__":
    main()