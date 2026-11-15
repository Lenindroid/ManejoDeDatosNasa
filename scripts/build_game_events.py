"""Curates the DONKI events that reach a lunar base and turns them into game-ready entries.
Usage: python -I scripts/build_game_events.py donki_data eventos_juego.json

Each event has: robot dialog (real alert + what to do), radiation points, blackout flag, arrival time (minutes)
and the chain it belongs to (events linked by DONKI, e.g. flare -> particle storm -> CME impact).
The dialogs are for kids 6 to 12: short, no jargon, the real date, and an analogy for each new idea."""
import json, os, sys, math, datetime as dt, collections as C

SRC, OUT = sys.argv[1], sys.argv[2]
PERIOD = sys.argv[3] if len(sys.argv) > 3 else "2024-01-01 to 2024-12-31"  # only used in the "source" text
L = lambda t: json.load(open(os.path.join(SRC, t + ".json")))
AU_KM = 149_597_870
EARTH_KM = 12_742  # diameter of the Earth, for speed comparisons
SUN_LIGHT_MIN = 8  # sunlight reaches the Earth-Moon system in ~8.3 minutes

def ts(s): return dt.datetime.strptime(s, "%Y-%m-%dT%H:%MZ")
def minutes(a, b): return round((ts(b) - ts(a)).total_seconds() / 60)
def nice_date(s): d = ts(s); return f"{d:%B} {d.day}, {d.year}"
def links(x): return [l["activityID"] for l in (x.get("linkedEvents") or [])]

# ---------------------------------------------------------------- who detected it
DETECTORS = {  # DONKI instrument prefix -> spacecraft name a kid can read
    "GOES-P": "NOAA's GOES weather satellite", "GOES-S": "NOAA's GOES weather satellite",
    "GOES": "NOAA's GOES weather satellite",
    "SOHO": "the SOHO space telescope", "STEREO A": "NASA's STEREO-A spacecraft",
    "ACE": "NASA's ACE spacecraft", "DSCOVR": "NOAA's DSCOVR satellite",
    "SOLAR-1": "NOAA's SOLAR-1 satellite", "IMAP": "NASA's IMAP spacecraft",
    "MODEL": "NASA's early-warning computer",
}
NEAR_EARTH = ("GOES", "SOHO", "ACE", "DSCOVR", "SOLAR-1", "IMAP", "MODEL")  # STEREO-A is far from the Moon

def spacecraft(inst):
    names = []
    for i in sorted(inst, key=lambda i: i.startswith("MODEL")):  # real spacecraft first
        n = DETECTORS.get(i.split(":")[0])
        if n and n not in names: names.append(n)
    return names

def spotter(inst):
    n = spacecraft(inst)
    return n[0] if n else "NASA's space weather team"

# ---------------------------------------------------------------- explanations (said once per event type)
EXPLAIN = {
 "FLR": ("A solar flare is like a giant camera flash on the Sun. Its light reaches the Moon in just 8 minutes! "
         "Scientists grade flares C, M and X, and X is the biggest."),
 "CME": ("Scientists call this a coronal mass ejection, or CME. It is like the Sun sneezing out a cloud of hot gas "
         "much bigger than the Earth. It takes one to four days to reach the Moon."),
 "SEP": ("These particles are tiny bits of atoms, faster than anything people have ever built. On Earth, the air and "
         "a magnetic shield protect us like an umbrella. The Moon has neither, so our walls are the umbrella!"),
 "IPS": ("A shock wave is like the wave in front of a fast boat: it arrives first and shakes everything it passes."),
 "HSS": ("Some parts of the Sun blow a faster wind, like a fan that is always on. It gives moon dust static, "
         "so it sticks to everything, like a balloon rubbed on your hair!"),
}

# ---------------------------------------------------------------- robot dialog: [real alert, what to do]
OPENERS = ["This really happened!", "Real NASA data!", "True story from space!"]

def kid_dialog(e):
    d, t, date, seen = e["data"], e["type"], nice_date(e["date"]), e["_seen_by"]
    if t == "FLR":
        x = d["class"][0] == "X"
        alert = f"On {date}, {seen} saw a solar flare of class {d['class']}." + (" That is the biggest kind!" if x else "")
        tip = ("Radiation may come next. Get the base ready and stay close to it!" if x
               else "Its flash can harm the solar panels. Check them!")
    elif t == "CME":
        speed = round(d["speed_kms"])
        alert = f"On {date}, {seen} saw the Sun throw a giant cloud of hot gas our way, at {speed} km per second."
        if speed: alert += f" That is fast enough to cross the whole Earth in {round(EARTH_KM / speed)} seconds!"
        tip = ("When it hits, the power will go out. Get the spare batteries ready!" if e["blackout"]
               else "It will only brush past us. Check the solar panels after it passes." if d["glancing_blow"]
               else "It is not very fast. Check the solar panels when it arrives.")
    elif t == "SEP":
        strength = "super strong " if e["blackout"] else "strong " if d["max_energy_mev"] >= 28 else ""
        alert = f"On {date}, {seen} detected a {strength}storm of tiny particles shooting out of the Sun."
        tip = ("It is so strong it can break machines! Stay inside, keep away from radiation zones and check the oxygen machine."
               if e["blackout"] else "Stay inside the base and keep away from radiation zones until it passes!")
    elif t == "IPS":
        alert = f"On {date}, {seen} felt a shock wave in the wind that blows from the Sun."
        tip = "It brings a little radiation. Check the solar panels after it passes!"
    else:  # HSS
        alert = f"On {date}, {seen} measured a fast wind blowing from the Sun."
        tip = "It makes moon dust stick to the solar panels. Time to clean them!"
    opener = OPENERS[sum(map(ord, e["id"])) % len(OPENERS)]  # same opener every time the file is rebuilt
    return [f"{opener} {alert}", tip]

NAMES = {"FLR": "Solar Flare", "SEP": "Solar Energetic Particle Event", "CME": "Coronal Mass Ejection",
         "IPS": "Interplanetary Shock", "HSS": "High Speed Solar Wind Stream"}

# ---------------------------------------------------------------- radiation scale (0-100 game points)
# DONKI does not give a radiation dose, so points are derived from what it does measure:
#   FLR: X-ray peak flux (log scale)  M1 = 5, X1 = 10, X10 = 15
#   SEP: highest proton energy measured near Earth  >10 MeV = 25, ~30-50 MeV = 40, >100 MeV = 60
#   IPS: shock-accelerated particles = 5;  CME direct hit (shock + plasma) = 5;  HSS = 0
def flare_flux(cls): return {"A": 1e-8, "B": 1e-7, "C": 1e-6, "M": 1e-5, "X": 1e-4}[cls[0]] * float(cls[1:] or 1)
def flare_points(cls): return max(1, round(5 * math.log10(flare_flux(cls) / 1e-6)))

def sep_energy(inst):
    """Highest energy channel (MeV) measured by near-Earth instruments."""
    best = 0
    for i in inst:
        if not i.startswith(NEAR_EARTH): continue
        rng = i.split()[-2].lstrip(">")  # ">10", "15.8-39.8", ">100"
        best = max(best, float(rng.split("-")[0]))
    return best

def sep_points(mev): return 60 if mev >= 100 else 40 if mev >= 28 else 25

events = {}
def add(tipo, eid, date, rad, blackout, arrival, source, seen_by, data, link, linked):
    events[eid] = {"id": eid, "type": tipo, "name": NAMES[tipo], "date": date,
                   "dialog": None, "_seen_by": seen_by,  # written at the end, once the event is final
                   "radiation_points": rad, "blackout": blackout,
                   "arrival_minutes": arrival, "arrival_source": source,
                   "data": data, "link": link, "_links": linked}

# ---------------------------------------------------------------- FLR: M and X class (C and below are negligible)
for x in L("FLR"):
    cls = x.get("classType") or "C"
    if cls[0] not in "MX": continue
    rise = max(SUN_LIGHT_MIN, minutes(x["beginTime"], x["peakTime"]))
    add("FLR", x["flrID"], x["beginTime"], flare_points(cls), False, rise, "observed: minutes from flare start to peak",
        spotter([i["displayName"] for i in x["instruments"]]),
        {"class": cls, "peak_time": x["peakTime"], "source_location": x.get("sourceLocation")}, x["link"], links(x))

# ---------------------------------------------------------------- IPS at Earth: real arrival time of CME shocks
ips = {x["activityID"]: x for x in L("IPS") if x.get("location") == "Earth"}

# ---------------------------------------------------------------- CME: only those that reach the Earth-Moon system
for x in L("CME"):
    an = next((a for a in (x.get("cmeAnalyses") or []) if a.get("isMostAccurate")), None)
    if not an: continue
    enlil = an.get("enlilList") or []
    model_arrival = next((e["estimatedShockArrivalTime"] for e in enlil if e.get("estimatedShockArrivalTime")), None)
    glancing = any(e.get("isEarthGB") for e in enlil) and not model_arrival
    if not (model_arrival or glancing): continue
    speed = an.get("speed") or 0
    shock_ids = [i for i in links(x) if i in ips]
    shock = sorted(ips[i]["eventTime"] for i in shock_ids)
    if shock:
        arrival, source = minutes(x["startTime"], shock[0]), "observed: shock measured at Earth"
    elif model_arrival:
        arrival, source = minutes(x["startTime"], model_arrival), "forecast: NASA WSA-ENLIL model"
    else:
        arrival, source = round(AU_KM / speed / 60), "estimate: 1 AU / measured speed"
    add("CME", x["activityID"], x["startTime"], 0 if glancing else 5, not glancing and speed >= 700, arrival, source,
        spotter([i["displayName"] for i in x["instruments"]]),
        {"speed_kms": speed, "half_angle_deg": an.get("halfAngle"), "glancing_blow": glancing,
         "shock_arrival": shock[0] if shock else model_arrival},
        x["link"], links(x))
    for i in shock_ids: ips[i]["_merged"] = True  # the shock is the CME arriving: not a separate event

# ---------------------------------------------------------------- SEP: only particle storms measured near Earth/Moon
for x in L("SEP"):
    inst = [i["displayName"] for i in x["instruments"]]
    mev = sep_energy(inst)
    if not mev: continue
    parents = [e for e in links(x) if e in events or e.split("-")[-2] in ("FLR", "CME")]
    starts = [events[p]["date"] for p in parents if p in events]
    if starts:
        arrival, source = max(1, minutes(min(starts), x["eventTime"])), "observed: minutes after its flare/CME began"
    else:
        arrival, source = None, None  # filled later with the typical delay
    add("SEP", x["sepID"], x["eventTime"], sep_points(mev), mev >= 100, arrival, source,
        spotter(inst),
        {"max_energy_mev": mev, "instruments": inst}, x["link"], links(x))

# ---------------------------------------------------------------- IPS not caused by a known CME
for i, x in ips.items():
    if x.get("_merged"): continue
    add("IPS", i, x["eventTime"], 5, False, None, None,
        spotter([d["displayName"] for d in x["instruments"]]),
        {"location": x["location"]}, x["link"], links(x))

# ---------------------------------------------------------------- HSS seen near Earth
for x in L("HSS"):
    inst = [i["displayName"] for i in x["instruments"]]
    if not any(i.startswith(NEAR_EARTH) for i in inst): continue
    add("HSS", x["hssID"], x["eventTime"], 0, False, round(AU_KM / 650 / 60), "estimate: 1 AU at a typical 650 km/s",
        spotter(inst),
        {}, x["link"], links(x))

# ---------------------------------------------------------------- merge duplicate SEPs
# DONKI logs one SEP per instrument/energy channel; those starting within 12 h are the same storm.
seps = sorted((e for e in events.values() if e["type"] == "SEP"), key=lambda e: e["date"])
groups = []
for e in seps:
    if groups and minutes(groups[-1][0]["date"], e["date"]) <= 12 * 60: groups[-1].append(e)
    else: groups.append([e])
for group in groups:
    keep = max(group, key=lambda e: e["data"]["max_energy_mev"])
    inst = sorted({i for e in group for i in e["data"]["instruments"]})
    mev = keep["data"]["max_energy_mev"]
    keep.update(date=group[0]["date"], radiation_points=sep_points(mev), blackout=mev >= 100)
    keep["data"]["instruments"] = inst
    keep["_seen_by"] = spotter(inst)
    known = [e for e in group if e["arrival_source"]]
    if known:
        first = min(known, key=lambda e: e["arrival_minutes"])
        keep["arrival_minutes"], keep["arrival_source"] = first["arrival_minutes"], first["arrival_source"]
    for d in group:
        if d is keep: continue
        keep["_links"] += d["_links"]
        keep.setdefault("merged_ids", []).append(d["id"])
        del events[d["id"]]

# fill unknown arrival times with the typical observed delay of their type
for t in ("SEP", "IPS"):
    known = sorted(e["arrival_minutes"] for e in events.values() if e["type"] == t and e["arrival_minutes"])
    typical = known[len(known) // 2] if known else (60 if t == "SEP" else 2 * 24 * 60)
    for e in events.values():
        if e["type"] == t and e["arrival_minutes"] is None:
            e["arrival_minutes"], e["arrival_source"] = typical, f"estimate: typical delay of {t} events in this dataset"

# ---------------------------------------------------------------- chains (connected events)
alias = {m: e["id"] for e in events.values() for m in e.get("merged_ids", [])}
adj = C.defaultdict(set)
for e in events.values():
    for l in e["_links"]:
        l = alias.get(l, l)
        if l in events and l != e["id"]: adj[e["id"]].add(l); adj[l].add(e["id"])
chains, seen = {}, set()
for eid in sorted(events, key=lambda i: events[i]["date"]):
    if eid in seen or not adj[eid]: continue
    comp, stack = [], [eid]; seen.add(eid)
    while stack:
        c = stack.pop(); comp.append(c)
        for n in adj[c]:
            if n not in seen: seen.add(n); stack.append(n)
    comp.sort(key=lambda i: (events[i]["date"], i))
    cid = f"chain-{len(chains) + 1:03d}"
    chains[cid] = comp
    for step, i in enumerate(comp, 1): events[i]["chain"] = {"id": cid, "step": step, "length": len(comp)}
for e in events.values():
    e.setdefault("chain", None); del e["_links"]
    e["dialog"] = kid_dialog(e); del e["_seen_by"]

ordered = sorted(events.values(), key=lambda e: e["date"])
out = {
 "source": f"NASA CCMC DONKI - https://ccmc.gsfc.nasa.gov/DONKI/ (real events, {PERIOD})",
 "setting": "Lunar base: only events that reach the Earth-Moon system are included.",
 "fields": {
   "dialog": "[0] real alert: date, who saw it and a comparison; [1] what to do in the base",
   "explanations": "One short analogy per event type. Say it the first time that type appears, between dialog[0] and dialog[1]",
   "radiation_points": "Extra radiation added to the environment, 0-100 game scale (see radiation_scale)",
   "blackout": "True if the event can knock out the base's power",
   "arrival_minutes": "Minutes from the robot's warning until the event hits the base",
   "arrival_source": "observed (real DONKI times), forecast (NASA model) or estimate (physics/typical value)",
   "chain": "Linked events (e.g. flare -> particle storm -> CME). Play them in 'step' order; null = standalone",
 },
 "radiation_scale": {
   "FLR": "X-ray peak flux, log scale: M1 = 5, X1 = 10, X10 = 15",
   "SEP": "Highest proton energy measured near Earth: >10 MeV = 25, ~30-50 MeV = 40, >100 MeV = 60",
   "CME": "Direct hit = 5 (shock particles), glancing blow = 0",
   "IPS": "5 (shock-accelerated particles)",
   "HSS": "0 (low-energy solar wind)",
 },
 "blackout_rules": {
   "CME": "Direct hit at >= 700 km/s: plasma charges the base and electric discharges can trip the power system",
   "SEP": "Only >100 MeV storms: particles cause electronic faults in the power system",
   "FLR": "No: light does not cut power on the Moon", "IPS": "No", "HSS": "No",
 },
 "excluded": "GST, RBE and MPC only happen inside Earth's magnetic field; CMEs not aimed at Earth; "
             "particles and solar wind measured only by STEREO-A (far from the Moon); C-class flares (negligible).",
 "summary": {
   "total": len(ordered),
   "by_type": dict(C.Counter(e["type"] for e in ordered)),
   "blackouts": sum(e["blackout"] for e in ordered),
   "with_radiation": sum(e["radiation_points"] > 0 for e in ordered),
   "chains": len(chains),
   "standalone": sum(e["chain"] is None for e in ordered),
 },
 "explanations": EXPLAIN,
 "chains": chains,
 "events": ordered,
}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out["summary"], indent=1))
