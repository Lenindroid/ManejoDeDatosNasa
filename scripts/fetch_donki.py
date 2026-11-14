import json, sys, urllib.request, datetime as dt, os, time
OUT = sys.argv[1]
start = dt.date(2025, 11, 14); end = dt.date(2026, 11, 14)
types = ["FLR","SEP","CME","GST","IPS","MPC","RBE","HSS"]
for t in types:
    allev = []; d = start
    while d < end:
        e = min(d + dt.timedelta(days=59), end)
        url = f"https://ccmc.gsfc.nasa.gov/DONKI/WS/get/{t}?startDate={d}&endDate={e}"
        for attempt in range(3):
            try:
                raw = urllib.request.urlopen(url, timeout=120).read().decode()
                data = json.loads(raw) if raw.strip() else []
                break
            except Exception as ex:
                print("retry", t, d, ex); time.sleep(3); data = []
        allev += data or []
        d = e + dt.timedelta(days=1)
    json.dump(allev, open(os.path.join(OUT, t + ".json"), "w"), indent=1)
    print(t, len(allev), flush=True)
