import json, sys, os, collections as C
D = sys.argv[1]
L = lambda t: json.load(open(os.path.join(D, t + ".json")))
def month(s): return s[:7]
# FLR
f = L("FLR"); cls = C.Counter(x["classType"][0] for x in f if x.get("classType"))
print("FLR por clase:", dict(cls))
print("FLR X:", [(x["peakTime"], x["classType"]) for x in f if x.get("classType","").startswith("X")])
print("FLR/mes:", dict(sorted(C.Counter(month(x["beginTime"]) for x in f).items())))
# CME
c = L("CME"); sp = []
for x in c:
    a = [an for an in (x.get("cmeAnalyses") or []) if an.get("isMostAccurate")]
    if a and a[0].get("speed"): sp.append(a[0]["speed"])
print("CME total", len(c), "con analisis", len(sp))
bins = C.Counter("<500" if s<500 else "500-1000" if s<1000 else "1000-1500" if s<1500 else ">=1500" for s in sp)
print("CME velocidad:", dict(bins))
earth = sum(1 for x in c for an in (x.get("cmeAnalyses") or []) if an.get("isMostAccurate") for e in (an.get("enlilList") or []) if e.get("isEarthGB") or e.get("estimatedShockArrivalTime"))
print("CME con impacto estimado (Enlil):", earth)
print("CME/mes:", dict(sorted(C.Counter(month(x["startTime"]) for x in c).items())))
# GST
g = L("GST")
for x in g:
    kp = max((k.get("kpIndex",0) for k in (x.get("allKpValues") or [])), default=None)
    print("GST", x["startTime"], "Kp max", kp)
# SEP
s = L("SEP"); print("SEP/mes:", dict(sorted(C.Counter(month(x["eventTime"]) for x in s).items())))
print("SEP instrumentos:", C.Counter(i["displayName"] for x in s for i in x.get("instruments",[])).most_common(6))
for t in ["IPS","MPC","RBE","HSS"]:
    k = L(t); key = "eventTime" if "eventTime" in k[0] else "startTime"
    print(t, "/mes:", dict(sorted(C.Counter(month(x[key]) for x in k).items())))
print("ejemplo SEP:", json.dumps(s[0])[:600])
print("ejemplo RBE:", json.dumps(L("RBE")[0])[:400])
