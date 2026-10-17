#!/usr/bin/env python3
"""Check an *arr media download pipeline is healthy end-to-end.

Verifies, without printing secrets:
  1. Sonarr/Radarr can reach their download client.
  2. The download client (e.g. qBittorrent) answers its API.
  3. Syncthing peers are paired and the configured folder is in sync.
  4. Sonarr/Radarr have the expected remote path mapping.

Usage: python3 health.py
Exits non-zero if any critical check fails.
"""
import sys, os, json, urllib.request, urllib.error, urllib.parse, ssl, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import load
cfg = load.load_dict()

fails = []
ok = []


def record(cond, label, detail=""):
    if cond:
        ok.append(f"  [OK]   {label}" + (f"  ({detail})" if detail else ""))
    else:
        fails.append(f"  [FAIL] {label}" + (f"  ({detail})" if detail else ""))
    return cond


qb = cfg.get("qbittorrent", {})
seed_host = cfg.get("pathmap", {}).get("host", "")
folder_id = cfg.get("syncthing_local", {}).get("folderId", "downloads")

# --- download client API ---
qbit_ok = False
if qb.get("url"):
    def qb_login(opener, base):
        d = urllib.parse.urlencode({"username": qb.get("user", ""),
                                    "password": qb.get("pass", "")}).encode()
        try:
            r = opener.open(urllib.request.Request(base + "/api/v2/auth/login", data=d,
                                                   method="POST", headers={"Referer": base + "/"}), timeout=25)
            return "Ok." in r.read(500).decode(errors="replace")
        except Exception:
            return False

    try:
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx),
                                         urllib.request.HTTPCookieProcessor(cj),
                                         urllib.request.HTTPRedirectHandler())
        qbit_ok = qb_login(op, qb["url"])
        record(qbit_ok, "Download client reachable/authenticated", qb.get("host", ""))
    except Exception as e:
        record(False, "Download client", str(e)[:60])
else:
    record(False, "Download client URL not configured")

# --- Sonarr/Radarr health + remote path mapping ---
for app in ("sonarr", "radarr"):
    url, key = cfg.get(app, {}).get("url"), cfg.get(app, {}).get("apiKey")
    if not url:
        record(False, f"{app.capitalize()} URL not configured")
        continue
    try:
        h = json.loads(urllib.request.urlopen(urllib.request.Request(
            f"{url}/api/v3/health", headers={"X-Api-Key": key}), timeout=10).read().decode())
        bad = [i for i in h if "DownloadClient" in i.get("source", "") and i.get("type") == "error"]
        record(not bad, f"{app.capitalize()} download client healthy",
               (bad[0]["message"][:60] if bad else "connected"))
    except Exception as e:
        record(False, f"{app.capitalize()} health query", str(e)[:50])
    if seed_host:
        try:
            m = json.loads(urllib.request.urlopen(urllib.request.Request(
                f"{url}/api/v3/remotepathmapping", headers={"X-Api-Key": key}), timeout=10).read().decode())
            good = any(x.get("host") == seed_host for x in m)
            record(good, f"{app.capitalize()} remote path map", f"{len(m)} mapping(s)")
        except Exception as e:
            record(False, f"{app.capitalize()} remote path", str(e)[:50])

# --- Syncthing on the media host ---
mt = cfg.get("syncthing_local", {})
if mt.get("url") and mt.get("apiKey"):
    try:
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        op.open(urllib.request.Request(mt["url"] + "/"), timeout=8)
        csrf = None; inst = mt.get("instance")
        for c in cj:
            if c.name.startswith("CSRF"):
                csrf = c.value; inst = c.name.replace("CSRF-Token-", "")
        H = {"X-API-Key": mt["apiKey"], "Accept": "application/json"}
        if inst:
            H["X-CSRF-Token-" + inst] = csrf
        st = json.loads(urllib.request.urlopen(urllib.request.Request(
            mt["url"] + f"/rest/db/status?folder={folder_id}", headers=H), timeout=10).read().decode())
        need = st.get("needFiles", 0); state = st.get("state")
        record(need == 0 and state in ("idle", "syncing"),
               f"Syncthing '{folder_id}' in-sync", f"state={state} need={need} files={st.get('globalFiles')}")
        seeddev = cfg.get("syncthing_seed", {}).get("deviceId")
        if seeddev:
            conn = json.loads(urllib.request.urlopen(urllib.request.Request(
                mt["url"] + "/rest/system/connections", headers=H), timeout=10).read().decode())
            seedconn = (conn.get("connections") or {}).get(seeddev, {}).get("connected", False)
            record(seedconn, "Syncthing media <-> seed connected", seeddev[:12] + "...")
    except Exception as e:
        record(False, "Syncthing media host query", str(e)[:60])

print("== Media pipeline health ==")
for line in ok:
    print(line)
for line in fails:
    print(line)
if fails:
    print(f"== RESULT: FAIL ({len(ok)} ok, {len(fails)} fail) ==")
else:
    print(f"== RESULT: ALL OK ({len(ok)}) ==")
sys.exit(1 if fails else 0)
