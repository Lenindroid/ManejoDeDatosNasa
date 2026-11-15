import json, sys, urllib.request, datetime as dt, os, time
# Usage: python -I scripts/fetch_donki.py donki_data [YYYY-MM-DD start] [YYYY-MM-DD end]
OUT = sys.argv[1]
start = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2024, 1, 1)
end = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date(2024, 12, 31)
types = ["FLR","SEP","CME","GST","IPS","MPC","RBE","HSS"]
for t in types:
    allev = []; d = start
    while d < end:
        e = min(d + dt.timedelta(days=59), end)
        url = f"https://ccmc.gsfc.nasa.gov/DONKI/WS/get/{t}?startDate={d}&endDate={e}"
        # DONKI limits requests (HTTP 429): wait longer on each retry, and stop if a chunk never arrives
        # so the year is not saved with silent gaps.
        for wait in (0, 10, 30, 90, 180):
            time.sleep(wait)
            try:
                raw = urllib.request.urlopen(url, timeout=120).read().decode()
                data = json.loads(raw) if raw.strip() else []
                break
            except Exception as ex:
                print("retry", t, d, ex, flush=True)
        else:
            sys.exit(f"FAILED {t} {d}..{e}: run the script again later")
        allev += data or []
        d = e + dt.timedelta(days=1)
    json.dump(allev, open(os.path.join(OUT, t + ".json"), "w"), indent=1)
    print(t, len(allev), flush=True)
